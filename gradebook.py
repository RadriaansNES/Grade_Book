## Calculate student grades via roster, homework, exam and quiz grades

from pathlib import Path
import pandas as pd
import numpy as np

HERE = Path(__file__).parent
DATA_FOLDER = HERE / "data"

## Load in roaster, selecting section/email/NID columns. Conversion to lowercase
roster = pd.read_csv(
    DATA_FOLDER / "roster.csv",
    converters={"NetID": str.lower, "Email Address": str.lower},
    usecols=["Section", "Email Address", "NetID"],
    index_col="NetID",
)

## Load in hw exam grades, selecting all sublists except submission (keyword). Conversion to lowercase
hw_exam_grades = pd.read_csv(
    DATA_FOLDER / "hw_exam_grades.csv",
    converters={"SID": str.lower},
    usecols=lambda x: "Submission" not in x,
    index_col="SID",
)

## Loading in quiz grades across multiple files, splitting by underscore and replacing with whitespace. Loop to extract email and grade
## Finally renaming to make each quiz specific, and concatenating for columns instead of rows
quiz_grades = pd.DataFrame()
for file_path in DATA_FOLDER.glob("quiz_*_grades.csv"):
    quiz_name = " ".join(file_path.stem.title().split("_")[:2])
    quiz = pd.read_csv(
        file_path,
        converters={"Email": str.lower},
        index_col=["Email"],
        usecols=["Email", "Grade"],
    ).rename(columns={"Grade": quiz_name})

    quiz_grades = pd.concat([quiz_grades, quiz], axis=1)


## Merging roster and homework grades together, combining for matching NID/SIDs
final_data = pd.merge(
    roster, hw_exam_grades, left_index=True, right_index=True,
)

# Merging quiz grades, using specified email as unique indentifier in lieu of NID/SID
final_data = pd.merge(
    final_data, quiz_grades, left_on="Email Address", right_index=True
)

# Replace NAN values with zero
final_data = final_data.fillna(0)

## Calculate exam scores 
for n in range(1, 4):
    final_data[f"Exam {n} Score"] = (
        final_data[f"Exam {n}"] / final_data[f"Exam {n} - Max Points"]
    )

## Calculate homework scores via total score. Using homework xx (-) as reg
homework_scores = final_data.filter(regex=r"^Homework \d\d?$", axis=1)
homework_max_points = final_data.filter(regex=r"^Homework \d\d? -", axis=1)

# Summing via columns
sum_of_hw_scores = homework_scores.sum(axis=1)
sum_of_hw_max = homework_max_points.sum(axis=1)
final_data["Total Homework"] = sum_of_hw_scores / sum_of_hw_max

# Calculate homework scores via average score
hw_max_renamed = homework_max_points.set_axis(homework_scores.columns, axis=1)
average_hw_scores = (homework_scores / hw_max_renamed).sum(axis=1)
final_data["Average Homework"] = average_hw_scores / homework_scores.shape[1]

# Take the maximum of two scoresets to determine which to use
final_data["Homework Score"] = final_data[["Total Homework", "Average Homework"]].max(axis=1)

## Calculate quiz scores. Same procedure as with homework scores but with using panda series to obtain quiz max score
quiz_scores = final_data.filter(regex=r"^Quiz \d$", axis=1)
quiz_max_points = pd.Series(
    {"Quiz 1": 11, "Quiz 2": 15, "Quiz 3": 17, "Quiz 4": 14, "Quiz 5": 12}
)

sum_of_quiz_scores = quiz_scores.sum(axis=1)
sum_of_quiz_max = quiz_max_points.sum()
final_data["Total Quizzes"] = sum_of_quiz_scores / sum_of_quiz_max

average_quiz_scores = (quiz_scores / quiz_max_points).sum(axis=1)
final_data["Average Quizzes"] = average_quiz_scores / quiz_scores.shape[1]

final_data["Quiz Score"] = final_data[
    ["Total Quizzes", "Average Quizzes"]
].max(axis=1)

## Calculate and assign letter grades
# Assign panda series to exam weights
weightings = pd.Series(
    {
        "Exam 1 Score": 0.05,
        "Exam 2 Score": 0.1,
        "Exam 3 Score": 0.15,
        "Quiz Score": 0.30,
        "Homework Score": 0.4,
    }
)

# Calculate final score via weightings
final_data["Final Score"] = (final_data[weightings.index] * weightings).sum(
    axis=1
)
# Turn final score into percent, rounding to the next highest integer
final_data["Ceiling Score"] = np.ceil(final_data["Final Score"] * 100)

# Assign grades via panda series
grades = {
    90: "A",
    80: "B",
    70: "C",
    60: "D",
    0: "F",
}

def grade_mapping(value):
    for key, letter in grades.items():
        if value >= key:
            return letter
        
letter_grades = final_data["Ceiling Score"].map(grade_mapping)
final_data["Final Grade"] = pd.Categorical(letter_grades, categories=grades.values(), ordered=True)

## Group data via section, then sort data via last name, first. Append to csv file
for section, table in final_data.groupby("Section"):
    section_file = DATA_FOLDER / f"Section {section} Grades.csv"
    num_students = table.shape[0]
    print(
        f"In Section {section} there are {num_students} students saved to "
        f"file {section_file}."
    )
    table.sort_values(by=["Last Name", "First Name"]).to_csv(section_file)
