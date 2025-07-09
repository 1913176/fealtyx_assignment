# students/views.py

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Student
from .serializers import StudentSerializer
import requests
import json
from concurrent.futures import ThreadPoolExecutor
from django.core.cache import cache

# Thread pool for handling concurrent requests
executor = ThreadPoolExecutor(max_workers=10)

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"

# def generate_student_summary(student_data):
#     prompt = f"""
#     Generate a concise and friendly summary for a student with the following details:
#     Name: {student_data['name']}
#     Age: {student_data['age']}
#     Email: {student_data['email']}
    
#     The summary should highlight the student's key attributes in a positive way, suitable for a school profile.
#     Keep it to 2-3 sentences maximum.
#     """
    
#     payload = {
#         "model": OLLAMA_MODEL,
#         "prompt": prompt,
#         "stream": False
#     }
    
#     try:
#         response = requests.post(OLLAMA_API_URL, json=payload)
#         response.raise_for_status()
#         result = response.json()
#         return result.get('response', 'No summary generated').strip()
#     except requests.RequestException as e:
#         return f"Could not generate summary: {str(e)}"

def generate_student_summary(student_data):
    try:
        # Try Ollama first
        prompt = f"Generate summary for {student_data['name']}"
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=10)
        response.raise_for_status()
        return response.json().get('response', '').strip()
    
    except requests.RequestException:
        # Fallback to simple summary
        return (
            f"{student_data['name']} is {student_data['age']} years old. "
            f"Contact at {student_data['email']}"
        )

@api_view(['GET', 'POST'])
def student_list(request):
    if request.method == 'GET':
        students = Student.objects.all()
        serializer = StudentSerializer(students, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = StudentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
def student_detail(request, pk):
    try:
        student = Student.objects.get(pk=pk)
    except Student.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = StudentSerializer(student)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = StudentSerializer(student, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        student.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
def student_summary(request, pk):
    cache_key = f'student_summary_{pk}'
    cached_summary = cache.get(cache_key)
    
    if cached_summary:
        return Response({'summary': cached_summary})
    
    try:
        student = Student.objects.get(pk=pk)
    except Student.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    serializer = StudentSerializer(student)
    student_data = serializer.data
    
    # Offload the summary generation to a thread pool
    future = executor.submit(generate_student_summary, student_data)
    summary = future.result()
    
    # Cache the summary for 1 hour
    cache.set(cache_key, summary, timeout=3600)
    
    return Response({'summary': summary})
