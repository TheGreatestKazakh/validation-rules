from django.db import models

class MessageVersion(models.Model):
    version_code = models.CharField(max_length=20, unique=True)
    xmlSchema = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.version_code

class Sender(models.Model):
    name = models.CharField(max_length=255)
    inn = models.CharField(max_length=20)

    def __str__(self):
        return self.name

class Message(models.Model):
    message_version = models.ForeignKey(MessageVersion, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    signature = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    sender = models.ForeignKey(Sender, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Message {self.id} ({self.message_version})"

class Operation(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    transaction_date = models.DateField()
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=10)
    operation_type = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.operation_type} {self.amount} {self.currency}"

class Members(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    member_name = models.CharField(max_length=255)

    def __str__(self):
        return self.member_name

class MessageXML(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    xml_content = models.TextField()
    xml_url_link = models.CharField(max_length=255)

class Error(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    error_code = models.CharField(max_length=100)
    error_message = models.TextField()

    def __str__(self):
        return f"{self.error_code}: {self.error_message}"

class DocumentFields(models.Model):
    field = models.CharField(max_length=100)
    version = models.ForeignKey(MessageVersion, on_delete=models.CASCADE)
    context = models.CharField(max_length=100)
    xpath = models.CharField(max_length=255)
    listmember = models.CharField(max_length=100, blank=True)
    tag = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.field

class Rule(models.Model):
    documentField = models.ForeignKey(DocumentFields, on_delete=models.CASCADE)
    version = models.ForeignKey(MessageVersion, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

class DataFormat(models.Model):
    rule = models.ForeignKey(Rule, on_delete=models.CASCADE)
    predicate = models.CharField(max_length=255)
    dataformat = models.CharField(max_length=255)
    length = models.CharField(max_length=50, blank=True)
    errorTemplate = models.TextField(blank=True)

class Requirement(models.Model):
    rule = models.ForeignKey(Rule, on_delete=models.CASCADE)
    predicate = models.CharField(max_length=255)
    isrequired = models.CharField(max_length=10)  # "True" / "False"
    errorTemplate = models.TextField(blank=True)
