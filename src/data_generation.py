# Importing Libraries
import io, os
import json
import boto3
import uuid
import random
import pandas as pd
import pytz
from datetime import *
from dotenv import load_dotenv

# Credentials
load_dotenv()
aws_region = "ap-south-1"
aws_access_key_id = os.environ.get("aws_access_key_id")
aws_secret_access_key = os.environ.get("aws_secret_access_key")

# s3 Location
s3_data_path = "s3://github-projects-resume/Chatstat-Plotly-Dashboard/data"
dashboard_data_path = f"{s3_data_path}/dashboard/output.csv"

# Data Parameters
TOTAL_ROWS = 200000

# Date Range
start_date = datetime(2024, 1, 1)
end_date = datetime.combine(datetime.now(tz=pytz.timezone("Asia/Kolkata")).date(), time(23, 59, 59, 999999))

# Users
users = [
    {
        "id": str(uuid.uuid4()),
        "name": "Kris Lubiniecki",
        "email": "klubiniecki@chatstat.com",
        "plan": "AI Guardian",
        "children": [
            {"id": str(uuid.uuid4()), "name": "Emma", "age": "Elementary", "gender": "Female", "email": "Emma@chatstat.com"},
            {"id": str(uuid.uuid4()), "name": "Oliver", "age": "Middle", "gender": "Male", "email": "Oliver@chatstat.com"},
        ],
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Jaskeerat Singh",
        "email": "jaskeerat.nonu@chatstat.com",
        "plan": "Privacy Protector",
        "children": [
            {"id": str(uuid.uuid4()), "name": "Naman", "age": "Middle", "gender": "Male", "email": "Naman@chatstat.com"},
            {"id": str(uuid.uuid4()), "name": "Aparna", "age": "High", "gender": "Female", "email": "Aparna@chatstat.com"},
            {"id": str(uuid.uuid4()), "name": "Kiran", "age": "Elementary", "gender": "Male", "email": "Kiran@chatstat.com"},
        ],
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Teng",
        "email": "j.teng@chatstat.com",
        "plan": "Essential Safety",
        "children": [
            {"id": str(uuid.uuid4()), "name": "Li Wei", "age": "High", "gender": "Male", "email": "Li.Wei@chatstat.com"},
            {"id": str(uuid.uuid4()), "name": "Chen Jie", "age": "Middle", "gender": "Female", "email": "Chen.Jie@chatstat.com"},
            {"id": str(uuid.uuid4()), "name": "Wang Fang", "age": "Elementary", "gender": "Female", "email": "Wang.Fang@chatstat.com"},
            {"id": str(uuid.uuid4()), "name": "Zhang Wei", "age": "Middle", "gender": "Male", "email": "Zhang.Wei@chatstat.com"},
        ],
    },
]

platforms = ["Facebook", "Instagram", "Tiktok", "Twitter", "Youtube", "Snapchat"]

# Alerts, result_contents, result_comments distribution
alert_weights = {"No": 0.7, "Low": 0.2, "Medium": 0.08, "High": 0.02}
result_contents_weights = {
    "Mental & Emotional Health": 0.45,
    "Sexual & Inappropriate Content": 0.25,
    "Other Toxic Content": 0.15,
    "Violence & Threats": 0.09,
    "Self Harm & Death": 0.06
}
result_comments_weights = {
    "No": 0.35,
    "Cyberbullying": 0.2,
    "Offensive": 0.15,
    "Sexually Suggestive": 0.12,
    "Sexually Explicit": 0.1,
    "Other": 0.08
}

user_distribution = {
    "klubiniecki@chatstat.com": int(TOTAL_ROWS * 0.25),
    "jaskeerat.nonu@chatstat.com": int(TOTAL_ROWS * 0.40),
    "j.teng@chatstat.com": int(TOTAL_ROWS * 0.35),
}

def random_date(start, end):
    delta = end - start
    rand_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=rand_seconds)

def weighted_choice(weights):
    return random.choices(list(weights.keys()), weights=list(weights.values()))[0]

def realistic_username(child_name, parent_name):
    base = child_name.lower().replace(" ", "")
    suffix = random.choice([str(random.randint(1,99)), parent_name.split()[0].lower(), ""])
    return f"{base}_{suffix}{random.randint(1,99)}".strip("_")

def final_to_s3(df):
    s3_client = boto3.client("s3", region_name=aws_region, aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key)

    bucket_name = dashboard_data_path.split("/")[2]
    key = "/".join(dashboard_data_path.split("/")[3:])

    buffer = io.BytesIO()
    df.to_csv(buffer, index=False)
    s3_client.put_object(Bucket=bucket_name, Key=key, Body=buffer.getvalue())
    return True


def lambda_handler(event=None, context=None):
    rows = []
    for user in users:
        count = user_distribution[user["email"]]
        for _ in range(count):
            child = random.choice(user["children"])
            platform = random.choice(platforms)

            # IDs
            acc_id = str(uuid.uuid4())
            content_id = str(uuid.uuid4())
            comment_id = str(uuid.uuid4())

            # Times
            content_time = random_date(start_date, end_date)
            comment_time = content_time + timedelta(minutes=random.randint(0, 1440))

            # Alerts & results
            alert_content = weighted_choice(alert_weights)
            result_content = weighted_choice(result_contents_weights)
            result_comment = weighted_choice(result_comments_weights)
            alert_comment = weighted_choice(alert_weights)

            row = {
                "id_users": user["id"],
                "children_users": f"{user['id']}_children",
                "name_users": user["name"],
                "email_users": user["email"],
                "plan_users": user["plan"],
                "id_childrens": child["id"],
                "accounts_childrens": f"{child['id']}_acc",
                "name_childrens": child["name"],
                "email_childrens": child["email"],
                "age_childrens": child["age"],
                "gender_childrens": child["gender"],
                "user_childrens": user["id"],
                "id_accounts": acc_id,
                "content_accounts": f"content_{uuid.uuid4().hex[:6]}",
                "username_accounts": realistic_username(child["name"], user["name"]),
                "platform_accounts": platform,
                "id_contents": content_id,
                "comments_contents": random.choice(["", "Nice post", "Toxic comment", "This is a comment"]),
                "platform_contents": platform,
                "createTime_contents": content_time.strftime("%Y-%m-%d %H:%M:%S"),
                "alert_contents": alert_content,
                "result_contents": result_content,
                "id_comments": comment_id,
                "commentTime_comments": comment_time.strftime("%Y-%m-%d %H:%M:%S"),
                "platform_comments": platform,
                "alert_comments": alert_comment if random.random() > 0.2 else "",
                "result_comments": result_comment,
            }
            rows.append(row)

    # Writing to s3
    df = pd.DataFrame(rows)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    final_to_s3(df)

    return {
        'statusCode': 200,
        'body': json.dumps('Data Processing Complete!')
    }

if __name__ == "__main__":
    lambda_handler()