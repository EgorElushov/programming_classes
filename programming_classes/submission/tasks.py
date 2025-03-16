from celery import shared_task
from django.conf import settings
import subprocess
import tempfile
import os
import traceback

@shared_task
def check_submission(submission_id):
    """
    Check a submission by running the code against test cases
    """
    from .models import Submission
    
    try:
        submission = Submission.objects.get(submission_id=submission_id)
        
        # Skip if the submission is already processed
        if submission.status != 'pending':
            return f"Submission {submission_id} already has status {submission.status}"
        
        # Get the problem and test cases (assuming you have a TestCase model)
        problem = submission.problem
        
        # For demonstration - in a real system you'd check against actual test cases
        # and would likely use Docker or some other containerization for security
        
        # Create a temporary file with the code
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
            f.write(submission.code.encode('utf-8'))
            temp_file = f.name
        
        try:
            # Execute the code (this is simplified and not secure!)
            # In a real implementation, you'd need proper sandboxing
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=5  # 5 second timeout
            )
            
            # Check if execution was successful
            if result.returncode == 0:
                # This is just a demo - in reality you'd compare output with expected results
                submission.status = 'accepted'
            else:
                submission.status = 'rejected'
                
            submission.save()
            
            # Clean up
            os.unlink(temp_file)
            
            return f"Submission {submission_id} processed. New status: {submission.status}"
            
        except subprocess.TimeoutExpired:
            submission.status = 'rejected'  # Time limit exceeded
            submission.save()
            # Clean up
            os.unlink(temp_file)
            return f"Submission {submission_id} timed out. Status set to: {submission.status}"
            
        except Exception as e:
            submission.status = 'rejected'  # Runtime error
            submission.save()
            # Clean up
            os.unlink(temp_file)
            return f"Error processing submission {submission_id}: {str(e)}"
            
    except Submission.DoesNotExist:
        return f"Submission {submission_id} not found"
    except Exception as e:
        return f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
