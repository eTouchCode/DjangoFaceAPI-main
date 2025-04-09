from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Company, AccessKey, CompanyRole, CompanyMember, Camera, WorkShift
from .serializers import CompanySerializer, CompanyRoleSerializer, CompanyMemberSerializer, CameraSerializer, WorkShiftSerializer
from django.utils import timezone
import json
import hashlib
import secrets
import re
import datetime
import face_recognition
import os
import pickle
from django.utils.text import get_valid_filename
from django.db import connection

from api.scheduler_utilities import *
from api.camera_utilities import *





# class TrainModel:
#     def __init__(self):
#         self.known_face_encodings = []
#         self.known_face_names = []
#         self.training_dir = 'training'
#         self.output_dir = 'output'
#         os.makedirs(self.training_dir, exist_ok=True)
#         os.makedirs(self.output_dir, exist_ok=True)

#     def encode_faces(self, company_hash):
#         for person_dir in os.listdir(self.training_dir):
#             person_path = os.path.join(self.training_dir, person_dir)
#             if not os.path.isdir(person_path):
#                 continue
            
#             for image_file in os.listdir(person_path):
#                 image_path = os.path.join(person_path, image_file)
#                 face_image = face_recognition.load_image_file(image_path)
#                 face_encodings = face_recognition.face_encodings(face_image)

#                 if not face_encodings:
#                     print(f"No faces found in {image_file}.")
#                     continue
                
#                 face_encoding = face_encodings[0]
#                 self.known_face_encodings.append(face_encoding)
#                 self.known_face_names.append(person_dir)
#                 print(f"Encoded face image {image_file} for {person_dir}")

#         output_file = os.path.join(self.output_dir, f'{company_hash}.pkl')
#         with open(output_file, 'wb') as file:
#             pickle.dump({'encodings': self.known_face_encodings, 'names': self.known_face_names}, file)
#         return "Training completed and model saved."

#     def add_images(self, images_with_names, company_hash):
#         for image, person_name in images_with_names:
#             person_dir = os.path.join(self.training_dir, person_name)
#             os.makedirs(person_dir, exist_ok=True)

#             # Use get_valid_filename to ensure the filename is safe
#             filename = get_valid_filename(image.name)
#             image_path = os.path.join(person_dir, filename)

#             # Save the image to the filesystem
#             with open(image_path, 'wb+') as destination:
#                 for chunk in image.chunks():
#                     destination.write(chunk)
        
#         return self.encode_faces(company_hash)


class TrainModel:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.training_dir = 'training'
        self.output_dir = 'output'
        os.makedirs(self.training_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def load_existing_encodings(self, company_hash):
        output_file = os.path.join(self.output_dir, f'{company_hash}.pkl')
        if os.path.exists(output_file):
            with open(output_file, 'rb') as file:
                data = pickle.load(file)
                self.known_face_encodings = data.get('encodings', [])
                self.known_face_names = data.get('names', [])
        else:
            print("No existing encodings found, starting fresh.")

    def encode_new_faces(self, images_with_names):
        new_encodings = []
        new_names = []

        print(f"Encoding faces for images: {images_with_names}")  # Debugging line

        for image, person_name in images_with_names:
            if not image or not person_name:
                print("Invalid image or person name")
                continue

            # Check if image is a FileStorage object
            if not hasattr(image, 'read'):
                print(f"Invalid image object: {image}")
                continue

            try:
                face_image = face_recognition.load_image_file(image)
                face_encodings = face_recognition.face_encodings(face_image)

                if not face_encodings:
                    print(f"No faces found in {image}.")
                    continue

                face_encoding = face_encodings[0]
                new_encodings.append(face_encoding)
                new_names.append(person_name)
                print(f"Encoded face image {image} for {person_name}")

            except Exception as e:
                print(f"Error processing image {image}: {e}")

        self.known_face_encodings.extend(new_encodings)
        self.known_face_names.extend(new_names)

    def save_encodings(self, company_hash):
        output_file = os.path.join(self.output_dir, f'{company_hash}.pkl')
        with open(output_file, 'wb') as file:
            pickle.dump({'encodings': self.known_face_encodings, 'names': self.known_face_names}, file)
        return "Training completed and model saved."

    def add_images(self, images_with_names, company_hash):
        # Save the new images in the respective directories
        for image, person_name in images_with_names:
            person_dir = os.path.join(self.training_dir, person_name)
            os.makedirs(person_dir, exist_ok=True)
            filename = get_valid_filename(image.name)
            image_path = os.path.join(person_dir, filename)
            # Save the image file
            with open(image_path, 'wb') as f:
                for chunk in image.chunks():
                    f.write(chunk)

        # Load existing encodings before adding new ones
        self.load_existing_encodings(company_hash)

        # Only encode new faces
        self.encode_new_faces(images_with_names)
        
        # Save all encodings
        return self.save_encodings(company_hash)
    

def validate_company(token):
    try:
        access_key = AccessKey.objects.get(access_key=token, enabled=True)
        company = access_key.company
        return {'id': company.id, 'company_hash': company.company_hash, 'name': company.name, 'callback_url': company.callback_url, 'access_key': access_key.access_key}
    except AccessKey.DoesNotExist:
        return None

def validate_and_format_url(url):
    # Check if the URL has a scheme (http or https)
    if not re.match(r'http[s]?://', url):
        # Default to https if no scheme is provided
        url = 'https://' + url
    return url

def generate_access_token():
    return secrets.token_hex(32)

def generate_company_hash(company_name):
    return hashlib.sha256(company_name.encode()).hexdigest()

@api_view(['POST'])
def insert_company_route(request):
    company_name = request.data.get('name')
    callback_url = request.data.get('callback_url')

    if not company_name or not callback_url:
        return Response({'error': 'name and callback_url are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Check if the company already exists
        if Company.objects.filter(name=company_name).exists():
            return Response({'error': f'Company {company_name} already exists'}, status=status.HTTP_400_BAD_REQUEST)

        callback_url = validate_and_format_url(callback_url)
        company_hash = generate_company_hash(company_name)
        access_token = generate_access_token()

        # Create the company
        company = Company.objects.create(
            company_hash=company_hash,
            name=company_name,
            callback_url=callback_url,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now()
        )

        # Create the access key
        AccessKey.objects.create(
            company=company,
            access_key=access_token,
            enabled=True,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now()
        )

        company_data = CompanySerializer(company).data
        company_data['access_key'] = access_token
        company_data['company_hash'] = company_hash
        
        return Response(company_data, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def create_role(request):
    token = request.headers.get('Access-Token')
    company = validate_company(token)
    if not company:
        return Response({'error': 'Invalid access token'}, status=status.HTTP_403_FORBIDDEN)
    
    role_name = request.data.get('role_name')
    if not role_name:
        return Response({'error': 'role_name is required'}, status=status.HTTP_400_BAD_REQUEST)

    if CompanyRole.objects.filter(role_name=role_name, company=company['id']).exists():
        return Response({'error': f"Role {role_name} already exists for the {company['name']}"}, status=status.HTTP_400_BAD_REQUEST)

    role = CompanyRole.objects.create(role_name=role_name, company_id=company['id'])
    return Response({'message': 'Role created successfully'}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def assign_member(request):
    token = request.headers.get('Access-Token')
    company = validate_company(token)
    if not company:
        return Response({'error': 'Invalid access token'}, status=status.HTTP_403_FORBIDDEN)

    member_name = request.data.get('member_name')
    role_name = request.data.get('role_name')
    if not member_name or not role_name:
        return Response({'error': 'member_name and role_name are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        role = CompanyRole.objects.get(role_name=role_name, company=company['id'])
    except CompanyRole.DoesNotExist:
        return Response({'error': f"Role {role_name} does not exist for the {company['name']}"}, status=status.HTTP_400_BAD_REQUEST)

    if CompanyMember.objects.filter(name=member_name, role=role, company=company['id']).exists():
        return Response({'error': 'Duplicate member name for the same role and company'}, status=status.HTTP_400_BAD_REQUEST)

    member = CompanyMember.objects.create(name=member_name, company_id=company['id'], role=role)
    return Response({'message': 'Member assigned to role successfully'}, status=status.HTTP_201_CREATED)

@api_view(['PUT'])
def update_assigned_member(request):
    token = request.headers.get('Access-Token')
    company = validate_company(token)
    if not company:
        return Response({'error': 'Invalid access token'}, status=status.HTTP_403_FORBIDDEN)

    member_name = request.data.get('member_name')
    role_name = request.data.get('role_name')
    if not member_name or not role_name:
        return Response({'error': 'member_name and role_name are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        role = CompanyRole.objects.get(role_name=role_name, company=company['id'])
    except CompanyRole.DoesNotExist:
        return Response({'error': f"Role {role_name} does not exist for the {company['name']}"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        member = CompanyMember.objects.get(name=member_name, company=company['id'])
        member.role = role
        member.save()
        return Response({'message': 'Member role updated successfully'}, status=status.HTTP_200_OK)
    except CompanyMember.DoesNotExist:
        return Response({'error': 'Member not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def get_company_members(request):
    token = request.headers.get('Access-Token')
    company_name = request.data.get('company_name')

    if not token or not company_name:
        return Response({'error': 'Access token and company name are required'}, status=status.HTTP_400_BAD_REQUEST)

    company = validate_company(token)
    if not company:
        return Response({'error': 'Invalid access token'}, status=status.HTTP_403_FORBIDDEN)

    if company_name != company['name']:
        return Response({'error': 'Access token and company name must be the same'}, status=status.HTTP_403_FORBIDDEN)

    members = CompanyMember.objects.filter(company_id=company['id']).select_related('role')
    members_list = [{'name': member.name, 'role': member.role.role_name} for member in members]

    return Response({'number_of_members': len(members_list), 'members': members_list}, status=status.HTTP_200_OK)

@api_view(['POST'])
def get_roles(request):
    token = request.headers.get('Access-Token')
    company_name = request.data.get('company_name')
    
    if not token:
        return Response({'error': 'Access token is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    company = validate_company(token)
    
    if not company:
        return Response({'error': 'Invalid access token'}, status=status.HTTP_403_FORBIDDEN)

    roles = CompanyRole.objects.filter(company_id=company['id'])
    roles_list = [{'role_name': role.role_name} for role in roles]

    return Response({'company_name': company['name'], 'roles': roles_list}, status=status.HTTP_200_OK)




@api_view(['POST'])
def add_camera(request):
    token = request.headers.get('Access-Token')
    company = validate_company(token)
    if not company:
        return Response(
            {'error': 'Invalid access token'}, 
            status=status.HTTP_403_FORBIDDEN
        )

    model_path = f"./output/{company['company_hash']}.pkl"
    if not os.path.exists(model_path):
        return Response(
            {'error': f"No model file found for the {company['name']}"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    nickname = request.data.get('nickname')
    ip = request.data.get('ip')
    port = request.data.get('port')
    user = request.data.get('user')
    password = request.data.get('password')
    channel = request.data.get('channel')
    enabled = request.data.get('enabled')
    loc = request.data.get('loc')
    rtsp_url = f"rtsp://{user}:{password}@{ip}:{port}/live/{channel}"
    
    if not ip or not port or not user or not password:
        return Response(
            {'error': 'IP, port, user, and password are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT id, enabled FROM api_camera
            WHERE ip = %s AND port = %s AND company_id = %s AND `user` = %s
        ''', [ip, port, company['id'], user])
        
        existing_camera = cursor.fetchone()

    if existing_camera:
        if existing_camera[1] == 0:
            start_camera_thread(
                existing_camera[0], 
                company['id'], 
                company['company_hash'], 
                company['callback_url'], 
                rtsp_url, 
                model_path, 
                loc
            )
        return Response(
            {
                'message': 'Camera already exists', 
                'camera_id': existing_camera[0]
            }, 
            status=status.HTTP_200_OK
        )

    camera_id = add_camera2(
        nickname, 
        ip, 
        port, 
        user, 
        password, 
        channel, 
        enabled, 
        company['id'], 
        company['company_hash'], 
        company['callback_url'], 
        rtsp_url, 
        model_path, 
        loc
    )
    
    return Response(
        {
            'message': 'Camera added successfully', 
            'camera_id': camera_id
        }, 
        status=status.HTTP_201_CREATED
    )





@api_view(['POST'])
def get_cameras(request):
    token = request.headers.get('Access-Token')
    company_name = request.data.get('company_name')

    if not token or not company_name:
        return Response({'error': 'Access token and company name are required'}, status=status.HTTP_400_BAD_REQUEST)

    company = validate_company(token)
    if not company:
        return Response({'error': 'Invalid access token'}, status=status.HTTP_403_FORBIDDEN)

    if company_name != company['name']:
        return Response({'error': 'Access token and company name must be the same'}, status=status.HTTP_403_FORBIDDEN)

    cameras = Camera.objects.filter(company_id=company['id'])
    cameras_list = [{'nickname': camera.nickname, 'ip': camera.ip, 'enabled': camera.enabled} for camera in cameras]

    return Response({'cameras': cameras_list}, status=status.HTTP_200_OK)


@api_view(['POST'])
def create_shift(request):
    token = request.headers.get('Access-Token')
    company = validate_company(token)
    if not company:
        return Response({'error': 'Invalid access token'}, status=status.HTTP_403_FORBIDDEN)

    shift_name = request.data.get('shift_name')
    shift_start_time = request.data.get('start_time')
    shift_end_time = request.data.get('endtime_time')

    if not shift_name or not shift_start_time or not shift_end_time:
        return Response({'error': 'shift_name, start_time, and endtime_time are required'}, status=status.HTTP_400_BAD_REQUEST)

    if WorkShift.objects.filter(company=company['id'], name=shift_name).exists():
        return Response({'error': 'Shift with the same name already exists for this company'}, status=status.HTTP_400_BAD_REQUEST)

    work_shift = WorkShift.objects.create(
        company_id=company['id'],
        name=shift_name,
        start_time=shift_start_time,
        end_time=shift_end_time
    )

    return Response({'message': 'Shift added successfully', 'shift': WorkShiftSerializer(work_shift).data}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def get_shifts(request):
    token = request.headers.get('Access-Token')
    company_name = request.data.get('company_name')

    if not token or not company_name:
        return Response({'error': 'Access token and company name are required'}, status=status.HTTP_400_BAD_REQUEST)


    company = validate_company(token)
    if not company:
        return Response({'error': 'Invalid access token'}, status=status.HTTP_403_FORBIDDEN)


    if company_name != company['name']:
        return Response({'error': 'Access token and company name must be the same'}, status=status.HTTP_403_FORBIDDEN)

    # Retrieve shifts associated with the company
    shifts = WorkShift.objects.filter(company=company['id']).values('id', 'name', 'start_time', 'end_time')

    return Response({'shifts': list(shifts)}, status=status.HTTP_200_OK)




@api_view(['POST'])
def train(request):
    token = request.headers.get('Access-Token')
    company = validate_company(token)
    if not company:
        return Response({'error': 'Invalid access token'}, status=403)

    if 'images' not in request.FILES or 'metadata' not in request.POST:
        return Response({"error": "No images or metadata provided"}, status=400)

    images = request.FILES.getlist('images')
    metadata = request.POST.get('metadata')

    try:
        metadata = json.loads(metadata)
    except ValueError:
        return Response({"error": "Invalid metadata format"}, status=400)

    images_with_names = []
    for person_name, indices in metadata.items():
        for index in indices:
            if 0 <= index < len(images):
                images_with_names.append((images[index], person_name))
            else:
                return Response({"error": f"Index {index} out of range for images list"}, status=400)

    train_model = TrainModel()
    result = train_model.add_images(images_with_names, company['company_hash'])
    
    return Response({"message": result}, status=200)