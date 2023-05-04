## Calculate student grades via roster, homework, exam and quiz grades

from pathlib import Path
import pandas as pd

HERE = Path(__file__).parent
DATA_FOLDER = HERE / "data"

## Load in roaster, selecting section/email/NID columns. Conversion to lowercase
roster = pd.read_csv(
    DATA_FOLDER / "roster.csv",
    converters={"NetID": str.lower, "Email Address": str.lower},
    usecols=["Section", "Email Address", "NetID"],
    index_col="NetID",
)

## Load in hw exam grades, selecting all sublists except submission time. Conversion to lowercase
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

## Merging quiz grades, using specified email as unique indentifier in lieu of NID/SID
final_data = pd.merge(
    final_data, quiz_grades, left_on="Email Address", right_index=True
)

print(final_data.head())