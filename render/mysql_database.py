# Importing Libraries
import os
import json
import boto3
import pandas as pd
import mysql.connector
from sqlalchemy import create_engine


def aws():
    # Setting up Boto3 Client
    region_name = "ap-southeast-2"
    secret_name = "rdsMYSQL"
    session = boto3.session.Session(region_name=region_name, aws_access_key_id=os.environ.get("aws_access_key_id"),
                                    aws_secret_access_key=os.environ.get("aws_secret_access_key"))
    sm_client = session.client(service_name="secretsmanager")

    # Reading Data from Secrets Manager
    try:
        get_secret_value_response = sm_client.get_secret_value(SecretId=secret_name)
        value = json.loads(get_secret_value_response["SecretString"])
    except Exception as e:
        print(e)
    return value

def get_data():
    # Establish Connection to MySQL
    value = aws()
    mysql_host = value["endpoint"]
    mysql_user = value["user"]
    mysql_password = value["password"]
    mysql_db = value["database"]

    mysql_connection = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}"
    mysql_engine = create_engine(mysql_connection)

    try:
        table_name = value["parent_table"]
        df = pd.read_sql(f"SELECT * FROM {table_name}", con=mysql_engine)
    finally:
        mysql_engine.dispose()
    return df

def post_report_metadata(data):
    # Establish Connection to MySQL
    value = aws()
    mysql_config = {
        "host": value["endpoint"],
        "user": value["user"],
        "password": value["password"],
        "database": value["database"]
    }
    mysql_connection = mysql.connector.connect(**mysql_config)

    # Insert Data into MySQL
    if mysql_connection.is_connected():
        query = f"""
        INSERT INTO dashboard.{value["report_metadata_table"]} 
        (email, children, timerange, platform, alert, contenttype) 
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        mysql_cursor = mysql_connection.cursor()
        mysql_cursor.execute(query, (data["email"], data["children"], json.dumps(data["timerange"]), json.dumps(data["platform"]),
                                     json.dumps(data["alert"]), json.dumps(data["contenttype"])))
        mysql_connection.commit()
        mysql_cursor.close()
        mysql_connection.close()
    return "Data inserted successfully"

def get_report_metadata(email):
    # Establish Connection to MySQL
    value = aws()
    mysql_host = value["endpoint"]
    mysql_user = value["user"]
    mysql_password = value["password"]
    mysql_db = value["database"]

    mysql_connection = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}"
    mysql_engine = create_engine(mysql_connection)

    try:
        table_name = value["report_metadata_table"]
        df = pd.read_sql(f"""SELECT * FROM {table_name} WHERE LOWER(email) = LOWER("{email}") ORDER BY created_at DESC""", con=mysql_engine)
    finally:
        mysql_engine.dispose()
    return df

if __name__ == "__main__":
    print("Connection to MySQL")
