FROM python:3.6-slim

RUN apt update && apt install -y gcc

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY parts/*py   parts/
COPY static/*    static/
COPY resources/* resources/
COPY main.py ./

EXPOSE 9998

CMD ["python", "main.py"]