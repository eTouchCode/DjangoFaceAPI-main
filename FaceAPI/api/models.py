# api/models.py
from django.db import models

class Company(models.Model):
    company_hash = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    callback_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class AccessKey(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    access_key = models.CharField(max_length=64)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Camera(models.Model):
    nickname = models.CharField(max_length=255, blank=True, null=True)
    ip = models.GenericIPAddressField()  # Changed from IP to ip
    port = models.IntegerField()
    user = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    channel = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    generated_id = models.CharField(max_length=255, blank=True, null=True)

class CompanyRole(models.Model):
    role_name = models.CharField(max_length=255)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CompanyMember(models.Model):
    name = models.CharField(max_length=255)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    role = models.ForeignKey(CompanyRole, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class AttendanceRecordV1(models.Model):
    user = models.ForeignKey(CompanyMember, on_delete=models.CASCADE)
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    status = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class AttendanceRecordV2(models.Model):
    user = models.ForeignKey(CompanyMember, on_delete=models.CASCADE)
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE)
    entrance_time1 = models.DateTimeField()
    entrance_time2 = models.DateTimeField(null=True, blank=True)
    exit_time1 = models.DateTimeField(null=True, blank=True)
    exit_time2 = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CameraEvent(models.Model):
    company_member = models.ForeignKey(CompanyMember, on_delete=models.CASCADE)
    event_time = models.DateTimeField(auto_now_add=True)
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE)

class WorkShift(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)