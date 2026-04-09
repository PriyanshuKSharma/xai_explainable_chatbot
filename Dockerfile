FROM python:3.10

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

EXPOSE 5000 8501

CMD ["bash", "-c", "python app.py & streamlit run ui.py"]