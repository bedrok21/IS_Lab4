from ortools.sat.python import cp_model
import pandas as pd
from tabulate import tabulate

# Дані для задачі
groups = {"G1": 30, "G2": 28, "G3": 30}
subjects = {
    "Math": {"hours": 4},
    "Biology": {"hours": 4},
    "CS": {"hours": 3},
    "Chemistry": {"hours": 3}
}
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
# Генерація унікальних тайм-слотів із прив'язкою до дня
time_slots = [f"{day}_T{i}" for day in days for i in range(1, 5)]

auditoriums = {"A1": 35, "A2": 40, "A3": 30}
lecturers = {"L1": ["Math"], "L5": ["CS"], "L7": ["Biology"], "L2": ["CS"], "L6": ["Biology"], "L3": ["Math"], "L8": ["Chemistry"], "L4": ["Chemistry"]}

# Ініціалізація моделі
model = cp_model.CpModel()

# Змінні
schedule = {}
for group in groups:
    for subject, data in subjects.items():
        for hour in range(data["hours"]):
            for time in time_slots:
                for room in auditoriums:
                    schedule[(group, subject, hour, time, room)] = model.NewBoolVar(
                        f"{group}_{subject}_{hour}_{time}_{room}"
                    )

# Обмеження
# 1. Група не може бути на двох заняттях одночасно
for group in groups:
    for time in time_slots:
        model.Add(
            sum(
                schedule[(group, subject, hour, time, room)]
                for subject, data in subjects.items()
                for hour in range(data["hours"])
                for room in auditoriums
            )
            <= 1
        )

# 2. Кожен предмет має бути призначений потрібній кількості годин для кожної групи
for group in groups:
    for subject, data in subjects.items():
        model.Add(
            sum(
                schedule[(group, subject, hour, time, room)]
                for hour in range(data["hours"])
                for time in time_slots
                for room in auditoriums
            )
            == data["hours"]
        )

# 3. Одна аудиторія не може бути зайнята одночасно кількома групами
for time in time_slots:
    for room in auditoriums:
        model.Add(
            sum(
                schedule[(group, subject, hour, time, room)]
                for group in groups
                for subject, data in subjects.items()
                for hour in range(data["hours"])
            )
            <= 1
        )

# 4. Викладач не може викладати більше ніж одну дисципліну одночасно
for lecturer, subjects_taught in lecturers.items():
    for time in time_slots:
        model.Add(
            sum(
                schedule[(group, subject, hour, time, room)]
                for group in groups
                for subject in subjects_taught
                for hour in range(subjects[subject]["hours"])
                for room in auditoriums
            )
            <= 1
        )

# 5. Розмір групи не перевищує місткість аудиторії
for group, group_size in groups.items():
    for subject, data in subjects.items():
        for hour in range(data["hours"]):
            for time in time_slots:
                for room, capacity in auditoriums.items():
                    if group_size > capacity:
                        model.Add(schedule[(group, subject, hour, time, room)] == 0)

# Оптимізація (мінімізуємо загальне використання слотів)
model.Minimize(
    sum(
        schedule[(group, subject, hour, time, room)]
        for group in groups
        for subject, data in subjects.items()
        for hour in range(data["hours"])
        for time in time_slots
        for room in auditoriums
    )
)


# Розв'язування
solver = cp_model.CpSolver()
status = solver.Solve(model)

if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    print("Розклад знайдено!")
    data = []
    for (group, subject, hour, time, room), var in schedule.items():
        if solver.Value(var):
            # Знаходимо лектора для предмета
            lecturer = next(
                (lecturer for lecturer, subjects_taught in lecturers.items() if subject in subjects_taught),
                "Unknown"
            )
            # Додавання результатів у таблицю
            day_name, time_slot = time.split("_")  # Розбивка тайм-слота
            data.append({
                "Group": group,
                "Subject": subject,
                "Hour": hour + 1,
                "Day": day_name,
                "Time Slot": time_slot,
                "Room": room,
                "Lecturer": lecturer
            })
    
    # Створення таблиці
    df = pd.DataFrame(data)
    df["Combined"] = df["Subject"] + "\n" + df["Room"] + "\n" + df["Lecturer"]
    pivot_table = df.pivot_table(
        index=["Day", "Time Slot"],
        columns="Group",
        values="Combined",
        aggfunc=lambda x: ', '.join(x)
    ).fillna('')

    # Сортування днів
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    pivot_table.reset_index(inplace=True)
    pivot_table['Day'] = pd.Categorical(pivot_table['Day'], categories=day_order, ordered=True)
    pivot_table.sort_values(by=["Day", "Time Slot"], inplace=True)

    print(tabulate(pivot_table, headers="keys", tablefmt="grid", showindex=False))
else:
    print("Розв'язок не знайдено.")

