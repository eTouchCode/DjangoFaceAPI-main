from django.urls import path
from .views import (
    insert_company_route,
    create_role,
    assign_member,
    update_assigned_member,
    get_company_members,
    get_roles,
    add_camera,
    get_cameras,
    create_shift,
    get_shifts,
    train,
)

urlpatterns = [
    path('insert-company', insert_company_route),
    path('create-role', create_role),
    path('assign-member', assign_member),
    path('update-member-role', update_assigned_member),
    path('get-company-members', get_company_members),
    path('get-company-roles', get_roles),
    path('add-camera', add_camera),
    path('get-cameras', get_cameras),
    path('add-work-shift', create_shift),
    path('get-shifts', get_shifts), 
    path('train', train),
]
