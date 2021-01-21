FROM python:3.9-slim
WORKDIR /code
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY settings.toml .
COPY .secrets.toml .
COPY setup.py .
COPY shedbot/ ./shedbot
RUN pip install .

ENV ENV_FOR_DYNACONF development

CMD ["python", "shedbot/main.py"]
