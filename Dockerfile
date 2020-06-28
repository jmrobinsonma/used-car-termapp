FROM python:3.8-slim-buster
WORKDIR /usr/src/app
COPY . /usr/src/app
RUN apt update && apt install -y python3-virtualenv
RUN python3 -m venv venv
RUN pip3 install -r requirements.txt
CMD ["python3", "__init__.py"]
