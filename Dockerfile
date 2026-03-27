FROM python:3.9

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

CMD ["bash", "-c", "python app.py & streamlit run ui.py"]