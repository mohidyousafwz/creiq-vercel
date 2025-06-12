FROM python:3.10

WORKDIR /app

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Install Playwright and browser dependencies
RUN apt-get update && apt-get install -y wget gnupg ca-certificates
RUN pip install playwright
RUN playwright install chromium

ENV PORT=8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
