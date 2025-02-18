FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ADD init.sh /
RUN chmod +x /init.sh
CMD [ "/init.sh"]