# Importing Libraries
import os, io
import json
import boto3
import s3fs
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from faker import Faker
import pyshorteners
from dotenv import load_dotenv

# Credentials
load_dotenv()
aws_region = "ap-south-1"
aws_access_key_id = os.environ.get("aws_access_key_id")
aws_secret_access_key = os.environ.get("aws_secret_access_key")

session = boto3.session.Session(region_name=aws_region, aws_access_key_id=os.environ.get("aws_access_key_id"),
                                    aws_secret_access_key=os.environ.get("aws_secret_access_key"))

# s3 Location
s3_data_path = "s3://github-projects-resume/Chatstat-Plotly-Dashboard/data"
dashboard_data_path = f"{s3_data_path}/dashboard/output.csv"
metadata_path = f"{s3_data_path}/metadata/"
report_file_path = f"{s3_data_path}/report/"


def read_s3():
    s3_client = session.client("s3")

    bucket_name = dashboard_data_path.split("/")[2]
    file_key = "/".join(dashboard_data_path.split("/")[3:])
    obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    data = obj['Body'].read().decode('utf-8')

    df = pd.read_csv(io.StringIO(data), header=0)
    df["createTime_contents"] = pd.to_datetime(df["createTime_contents"], format="%Y-%m-%d %H:%M:%S")
    df["commentTime_comments"] = pd.to_datetime(df["commentTime_comments"], format="%Y-%m-%d %H:%M:%S")
    return df


def get_info(df, user_logged_in_email):
    df = df[df["email_users"] == user_logged_in_email]
    user_info = df[["name_users", "email_users", "plan_users"]].iloc[0]
    return user_info


def post_report_metadata(payload, current_time):
    s3_client = session.client("s3")

    new_metadata_path = metadata_path + "{}.json".format(current_time.strftime('%Y_%m_%d_%H_%M_%S_%f'))
    bucket_name = new_metadata_path.split("/")[2]
    key = "/".join(new_metadata_path.split("/")[3:])
    json_payload = json.dumps(payload, indent=4)

    s3_client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json_payload,
        ContentType="application/json"
    )
    return True


def get_report_metadata():
    fs = s3fs.S3FileSystem(
        key=aws_access_key_id,
        secret=aws_secret_access_key,
        client_kwargs={'region_name': aws_region}
    )
    all_files = fs.glob(f"{metadata_path}*.json")

    if len(all_files) > 0:
        dfs = []
        for file in all_files:
            s3_path = f"s3://{file}"

            with fs.open(s3_path, 'r') as f:
                payload = json.load(f)

            df_part = pd.json_normalize([payload])
            df_part["last_modified"] = pd.to_datetime(fs.info(s3_path)["LastModified"])
            dfs.append(df_part)

        final_df = pd.concat(dfs, ignore_index=True)
        final_df = final_df.sort_values(by=["last_modified"], ascending=False)
        return final_df
    else:
        return pd.DataFrame()


def generate_report(df, payload, send_buffer=None, preview=False):
    fake = Faker()
    shortener = pyshorteners.Shortener(timeout=10)
    current_time = datetime.now()

    # Filtering Data
    df = df[(df["email_users"] == payload["email"]) & (df["name_childrens"] == payload["children"])]

    start_date, end_date = pd.to_datetime(payload["timerange"])
    df = df[pd.to_datetime(df["createTime_contents"]).between(start_date, end_date)]

    df = df[df["platform_contents"].str.lower().isin(payload["platform"])]
    df = df[df["alert_contents"].str.lower().isin(payload["alert"])]
    df = df[["email_users", "name_childrens", "platform_contents", "createTime_contents", "alert_contents"]]

    df["type"] = np.random.choice(payload["contenttype"], size=len(df))
    df["text"] = [fake.sentence() for _ in range(len(df))]

    df = df.rename(columns={
        "email_users": "email",
        "name_childrens": "name",
        "platform_contents": "platform",
        "createTime_contents": "datetime",
        "alert_contents": "alert"
    })
    if preview:
        return df

    # Writing data to s3
    s3_client = session.client("s3")
    bucket_name = report_file_path.split("/")[2]

    if payload["filetype"] == "xlsx":
        key = "/".join(report_file_path.split("/")[3:]) + f"excel/export_{current_time.strftime('%Y_%m_%d_%H_%M_%S_%f')}.xlsx"

        file_buffer = io.BytesIO()
        df.to_excel(file_buffer, index=False)
        data_bytes = file_buffer.getvalue()

        file_buffer.seek(0)
        s3_client.upload_fileobj(file_buffer, bucket_name, key)
    elif payload["filetype"] == "pdf":
        key = "/".join(report_file_path.split("/")[3:]) + f"pdf/export_{current_time.strftime('%Y_%m_%d_%H_%M_%S_%f')}.pdf"

        fig, ax = plt.subplots(figsize=(12, 9))
        ax.axis("off")
        table = ax.table(
            cellText=df.values,
            colLabels=df.columns,
            cellLoc="center",
            loc="center"
        )
        table.set_fontsize(10)
        table.scale(1.2, 1.2)

        col_widths = []
        for i, col in enumerate(df.columns):
            max_len = max([len(str(col))] + [len(str(val)) for val in df.iloc[:, i]] )
            col_widths.append(max_len)

        col_widths = [w / max(col_widths) for w in col_widths]
        for (row, col), cell in table.get_celld().items():
            cell.set_width(col_widths[col] * 0.9)

        file_buffer = io.BytesIO()
        plt.savefig(file_buffer, format="pdf", bbox_inches="tight")
        data_bytes = file_buffer.getvalue()

        file_buffer.seek(0)
        plt.close(fig)
        s3_client.upload_fileobj(file_buffer, bucket_name, key)

    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": key},
        ExpiresIn=900
    )
    url = shortener.tinyurl.short(url)

    if send_buffer is None:
        return df, url
    else:
        return df, url, data_bytes


if __name__ == "__main__":
    print("Dash Application Functions")