FROM python:3.13  
 
# Create the app directory
RUN mkdir /app
 
# Set the working directory inside the container
WORKDIR /app
 
# Set environment variables 
# Prevents Python from writing pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
#Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1 
 
# Upgrade pip
RUN pip install --upgrade pip 
 
# Copy the Django project  and install dependencies
COPY requirements.txt  /app/
 
RUN pip install --no-cache-dir -r requirements.txt
 
COPY . /app/
 
EXPOSE 8000
 
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
CMD ["celery", "-A", "programming_classes", "worker", "-l", "info"]