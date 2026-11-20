FROM python:3.14-slim
# can you find a lighter image?

WORKDIR /app

# copy the requirements file in the workdir
COPY requirements.txt .

# install the Python requirements
RUN pip install -r requirements.txt

# copy the app files and directories
COPY movie/ .

EXPOSE 3200 

# start movie.py when the container is started
CMD ["python", "movie.py"]
