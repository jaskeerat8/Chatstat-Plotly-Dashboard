View Dashboard Here - http://54.66.134.81:8001/ (Give a min to load) or https://chatstatdash.onrender.com (Give 2 min to load and refresh)

* The process followed in the backend to drive the flask app developed using Plotly Dash.
* The application uses a live mongodb database that serves as the source.
* AWS Glue pipeline is used to transform the data using an ETL process. Work Flow is used to Schedule the different Stages of the process.
* AWS EventBridge is used to trigger a Refresh and start the process every 1 hour.
* AWS S3 is used to store the Data during the raw, staging and final process.
![image](https://github.com/user-attachments/assets/0729ef15-c80b-4d3d-869e-ac4da7d3de70)
* The final data is saved on s3, that will be used to drive the application that consists of 3 pages - Dashboard, Analytics and Reports Page.
![Chatstat Dashboard](https://github.com/user-attachments/assets/b8cc92c4-5bdc-4006-a3db-bc74a7b97984)
