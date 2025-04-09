# api/serializers.py
from rest_framework import serializers
from .models import Company, AccessKey, Camera, CompanyRole, CompanyMember, AttendanceRecordV1, AttendanceRecordV2, CameraEvent, WorkShift

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'

class AccessKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessKey
        fields = '__all__'

class CameraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Camera
        fields = '__all__'

class CompanyRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyRole
        fields = '__all__'

class CompanyMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyMember
        fields = '__all__'

class AttendanceRecordV1Serializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRecordV1
        fields = '__all__'

class AttendanceRecordV2Serializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRecordV2
        fields = '__all__'

class CameraEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CameraEvent
        fields = '__all__'


class WorkShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkShift
        fields = '__all__'