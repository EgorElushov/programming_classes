import docker
import os
import requests
import subprocess
import tempfile
import time
import uuid
from celery import shared_task
from django.conf import settings
from problem.models import TestCase, TestResult
from submission.models import Submission


@shared_task
def check_submission(submission_id):
    """
    Проверяет отправленное решение
    """
    try:
        submission = Submission.objects.get(submission_id=submission_id)
        submission.status = 'pending'
        submission.save()

        # Получаем тесты
        test_cases = TestCase.objects.filter(problem=submission.problem).order_by('order')
        if not test_cases.exists():
            submission.status = 'rejected'
            submission.save()
            return f"No test cases found for problem {submission.problem.problem_id}"

        # Запускаем проверку
        failed = False

        for test_case in test_cases:
            result = run_test(submission, test_case)
            if result.result != 'AC':
                failed = True

            if failed and test_case.is_sample:
                break

        submission.status = 'accepted' if not failed else 'rejected'
        submission.save()

        return f"Submission {submission_id} checked: {submission.status}"

    except Submission.DoesNotExist:
        return f"Submission {submission_id} not found"
    except Exception as e:
        return f"Error checking submission {submission_id}: {str(e)}"
    

def python_solution(submission, test_case, temp_dir):
    with open(os.path.join(temp_dir, "solution.py"), 'w') as f:
            f.write(submission.code)
            
    with open(os.path.join(temp_dir, "input.txt"), 'w') as f:
        f.write(test_case.input_data)
    
    with open(os.path.join(temp_dir, "Dockerfile"), 'w') as f:
        f.write("""
        FROM python:3.9-alpine
        WORKDIR /app
        COPY solution.py /app/
        COPY input.txt /app/
        CMD ["python", "solution.py", "<", "input.txt"]
        """)

def cpp_solution(submission, test_case, temp_dir):
    with open(os.path.join(temp_dir, "solution.cpp"), 'w') as f:
        f.write(submission.code)
    
    with open(os.path.join(temp_dir, "input.txt"), 'w') as f:
        f.write(test_case.input_data)
    
    with open(os.path.join(temp_dir, "Dockerfile"), 'w') as f:
        f.write("""
        FROM gcc:4.9
        WORKDIR /app
        COPY solution.cpp /app/
        COPY input.txt /app/
        RUN g++ -o solution solution.cpp
        CMD ["./solution", "<", "input.txt"]
        """)

def run_test(submission, test_case):
    with tempfile.TemporaryDirectory() as temp_dir:
        if submission.programming_language == 'python':
            command = ["sh", "-c", "python /app/solution.py < /app/input.txt"]
            python_solution(submission, test_case, temp_dir)
        elif submission.programming_language == 'cpp':
            command = ["sh", "-c", "./solution < /app/input.txt"]
            cpp_solution(submission, test_case, temp_dir)
        
        try:
            client = docker.DockerClient(base_url=settings.DOCKER_BASE_URL)
            
            image_name = f"submission_{submission.submission_id}_{uuid.uuid4().hex[:8]}"
            
            print(f"Building Docker image {image_name} from {temp_dir}")
            image, build_logs = client.images.build(
                path=temp_dir,
                tag=image_name,
                rm=True
            )
            
            start_time = time.time()
            try:
                container = client.containers.run(
                    image.id,
                    command=command,
                    remove=True,
                    detach=False,
                    mem_limit="128m",
                    cpu_quota=100000,
                    cpu_period=100000,
                    network_disabled=True
                )
                
                execution_time = int((time.time() - start_time) * 1000)
                
                output = container.decode('utf-8')
                
                expected_output = test_case.expected_output.strip()
                actual_output = output.strip()
                
                if actual_output == expected_output:
                    result = "AC"
                    error_message = ""
                else:
                    result = "WA"
                    error_message = f"Expected: '{expected_output}', Got: '{actual_output}'"
                
                memory_used = 0
                
            except Exception as e:
                result = "SE"
                execution_time = int((time.time() - start_time) * 1000)
                error_message = str(e)
                actual_output = ""
                memory_used = 0
                
        except Exception as e:
            result = "SE"
            execution_time = 0
            error_message = str(e)
            actual_output = ""
            memory_used = 0
            
        finally:
            try:
                client.images.remove(image_name, force=True)
            except:
                pass
        
        test_result = TestResult.objects.create(
            submission=submission,
            test_case=test_case,
            result=result,
            execution_time=execution_time,
            memory_used=memory_used,
            output=actual_output,
            error_message=error_message
        )
        
        return test_result
