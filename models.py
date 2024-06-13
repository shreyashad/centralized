import uuid
import json
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractBaseUser,PermissionsMixin,BaseUserManager
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth.hashers import check_password
from roles.models import *
from accounts.base import BaseModel
from django.core.exceptions import ValidationError

# Create your models here.

class OrgType(models.TextChoices):
    MDINDIA = 'MDIndia', 'MDIndia'
    INSURANCE_COMPANY = 'Insurance Company', 'Insurance Company'
    BROKER = 'Broker', 'Broker'
    CORPORATE = 'Corporate', 'Corporate'

class LocationType(models.TextChoices):
    HO = 'HO', 'HO'
    RO = 'RO', 'RO'
    DO = 'DO', 'DO'
    UO = 'UO', 'UO'
    BRANCH = 'BRANCH', 'Branch'

class Gender(models.TextChoices):
    MALE = 'Male', 'Male'
    FEMALE = 'Female', 'Female'
    OTHERS = 'Others', 'Others'




class Organization(BaseModel):
    name = models.CharField(max_length=250,unique=True)
    org_type = models.CharField(max_length=150 ,choices=OrgType.choices)

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"


    def __str__(self):
        return self.name


class OrganizationSubType(BaseModel):
    org_type = models.CharField(max_length=150, choices=OrgType.choices)
    subtype = models.CharField(max_length=250, unique=True)

    def clean(self):
        if not Organization.objects.filter(org_type=self.org_type).exists():
            raise ValidationError(f"Organization Type with '{self.org_type}' does not exist.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Organization Sub Type"
        verbose_name_plural = "Organization Sub Types"

    def __str__(self):
        return f"{self.org_type} - {self.subtype}"




class Locations(BaseModel):
    org_type = models.CharField(max_length=150)
    org_name = models.CharField(max_length=250)
    location_type = models.CharField(max_length=150, choices=LocationType.choices)
    location_name = models.CharField(max_length=250)
    location_code = models.CharField(max_length=150)

    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "Locations"




class Department(BaseModel):
    name = models.CharField(max_length=250, unique=True)

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    def __str__(self):
        return self.name


class Designation(BaseModel):
    name = models.CharField(max_length=250, unique=True)

    class Meta:
        verbose_name = "Designation"
        verbose_name_plural = "Designations"


    def __str__(self):
        return self.name



class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('Username must be set')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, password, **extra_fields)


class CustomUser(AbstractBaseUser,PermissionsMixin):
    id = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False, db_index=True, primary_key=True
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    org_type = models.CharField(max_length=150)
    org_name = models.CharField(max_length=250)
    org_sub_type = models.CharField(max_length=150)
    location_type = models.CharField(max_length=150)
    location_name = models.CharField(max_length=250)
    location_code = models.CharField(max_length=150)
    emp_code = models.CharField(max_length=150)
    department = models.CharField(max_length=250)
    designation = models.CharField(max_length=250)
    mobile = PhoneNumberField(null=False, blank=False, unique=True)
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)
    assigned_pol_no = models.CharField(max_length=1000)
    is_online = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_authenticator = models.BooleanField(default=False)
    is_site_admin = models.BooleanField(default=False)
    last_password_change = models.DateTimeField(null=True, blank=True)
    password_change_required = models.BooleanField(default=False)
    password_history_json = models.TextField(default='[]')

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['mobile']

    @property
    def password_history(self):
        return json.loads(self.password_history_json)

    @password_history.setter
    def password_history(self,value):
        self.password_history_json = json.dumps(value)

    def is_password_expired(self):
        if not self.last_password_change:
            return False
        return (timezone.now() - self.last_password_change).days >= 30

    def is_password_in_history(self, raw_password):
        for hashed_password in self.password_history:
            if check_password(raw_password, hashed_password):
                return True
        return False

    def set_password(self, raw_password):
        if self.is_password_in_history(raw_password):
            raise ValidationError("The new password cannot be the same as any of the last 3 password.")
        super().set_password(raw_password)
        self.last_password_change = timezone.now()
        password_history = self.password_history
        password_history.append(self.password)
        if len(self.password_history) > 3:
            self.password_history.pop(0)
        self.password_history = password_history

    def save(self, *args, **kwargs):
        if self.password_change_required and not self.is_password_expired():
            self.password_change_required = False
        super().save(*args, **kwargs)



def user_directory_path(instance, filename):
    return f'user_{instance.user_id}/{filename}'


class UserProfile(BaseModel):
    GENDER = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Others', 'Others'),
    ]
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20,choices=GENDER)
    bio = models.TextField()
    roles = models.ManyToManyField(Role)
    Profile_pic = models.ImageField(upload_to=user_directory_path)

    class Meta:
        verbose_name = "UserProfile"
        verbose_name_plural = "UserProfiles"
        db_table = "UserProfile"
        ordering = ("-created_at",)


    def __str__(self):
        return f"{self.user.username}<{self.user.org_name}>"

    @property
    def user_details(self):
        return {
            'id': self.user.id,
            'username': self.user.username,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'org_type': self.user.org_type,
            'org_name': self.user.org_name,
            'org_sub_type': self.user.org_sub_type,
            'location_type': self.user.location_type,
            'location_name': self.user.location_name,
            'location_code': self.user.location_code,
            'emp_code': self.user.emp_code,
            'department': self.user.department,
            'is_active': self.user.is_active,
            'is_verified': self.user.is_verified,
            'is_online': self.user.is_online,
            'is_authenticator': self.user.is_authenticator,
            'is_site_admin': self.user.is_site_admin,
            'profile_pic': self.Profile_pic,
            'roles': [role.name for role in self.roles.all()],


        }


class UserSubTypeSpecificMapping(BaseModel):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    subtype = models.CharField(max_length=150)
    details = models.TextField()

    class Meta:
        verbose_name = "User Sub Type Specific Mapping "
        verbose_name_plural = "User Sub Type Specific Mappings"

