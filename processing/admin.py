from django.contrib import admin
from .models import Message, Error, MessageVersion, DocumentFields, DataFormat, Requirement, Operation, Sender, Members, MessageXML
admin.site.register([Message, Error, MessageVersion, DocumentFields, DataFormat, Requirement, Operation, Sender, Members, MessageXML])
