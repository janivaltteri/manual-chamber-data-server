from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Project(models.Model):
    measurer = models.ForeignKey(User, on_delete=models.PROTECT, blank=False,
                                 null=False, related_name='projects')
    date          = models.DateTimeField(default=timezone.now)
    name          = models.CharField(max_length=60)
    contact_name  = models.CharField(max_length=60)
    contact_email = models.CharField(max_length=60)

    def __str__(self):
        return u'{0}'.format(self.name)

class Measurements(models.Model):
    MEAS_STATUS_CHOICES = (
        ('submitted','Submitted'),
        ('processed','Processed'),
        ('retracted','Retracted'),
    )
    FILE_STATUS_CHOICES = (
        ('undetermined','Undetermined'),
        ('valid','Valid'),
        ('invalid','Invalid'),
    )
    DEVICE_CHOICES = (
        ('licor','Licor'),
        ('licorsmart','LicorSmart'),
        ('gasmet','Gasmet'),
        ('egm4','EGM4'),
        ('egm5','EGM5'),
    )
    CHAMBER_CHOICES = (
        ('dark','Dark'),
        ('light','Light'),
    )
    SOIL_CHOICES = (
        ('forested','Forested'),
        ('agricultural','Agricultural'),
    )
    FFTYPE_CHOICES = (
        ('legacy','Legacy'),
        ('2022','2022'),
    )
    measurer      = models.ForeignKey(User, on_delete=models.PROTECT, blank=False,
                                      null=False, related_name='submissions')
    project       = models.ForeignKey(Project, on_delete=models.PROTECT, blank=False,
                                      null=False, related_name='submissions')
    ##fsid_old      = models.IntegerField(blank=True, null=True) # from v1
    date          = models.DateTimeField(default=timezone.now)
    measure_date  = models.DateField()
    soil          = models.CharField(max_length=20, choices=SOIL_CHOICES)
    chamber       = models.CharField(max_length=10, choices=CHAMBER_CHOICES)
    fftype        = models.CharField(max_length=10, choices=FFTYPE_CHOICES)
    status        = models.CharField(max_length=10, choices=MEAS_STATUS_CHOICES,
                                     default='submitted')
    comment       = models.CharField(max_length=256, blank=True, null=True)
    device        = models.CharField(max_length=12, choices=DEVICE_CHOICES,
                                     default='undetermined')
    datastatus    = models.CharField(max_length=12, choices=FILE_STATUS_CHOICES,
                                     default='undetermined')
    datafilepath  = models.CharField(max_length=60)
    dataorigname  = models.CharField(max_length=100)
    fieldstatus   = models.CharField(max_length=12, choices=FILE_STATUS_CHOICES,
                                     default='undetermined')
    fieldfilepath = models.CharField(max_length=60)
    fieldorigname = models.CharField(max_length=100)
