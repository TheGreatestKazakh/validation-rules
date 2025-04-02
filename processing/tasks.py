import os
import re
from datetime import datetime

from celery import shared_task
from lxml import etree
from django.conf import settings
from .models import (
    Message, MessageVersion, Sender, Operation, Members,
    MessageXML, Error, DocumentFields, DataFormat, Requirement
)
from minio import Minio

IN_FOLDER = os.path.join(os.getcwd(), 'IN')
OUT_FOLDER = os.path.join(os.getcwd(), 'OUT')
os.makedirs(IN_FOLDER, exist_ok=True)
os.makedirs(OUT_FOLDER, exist_ok=True)


def get_minio_client():
    return Minio(
        settings.MINIO_ENDPOINT.replace('http://', '').replace('https://', ''),
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=False
    )

def process_xml_file(file_path):
        file_name = os.path.basename(file_path)
    # try:
        parser = etree.XMLParser(recover=False)
        tree = etree.parse(file_path, parser)
        root = tree.getroot()

        version_text = (root.findtext('./Version') or '').strip()
        if not version_text:
            raise ValueError("Не указана версия сообщения (Version)")

        try:
            version_obj = MessageVersion.objects.get(version_code=str(version_text))
        except MessageVersion.DoesNotExist:
            raise ValueError(f"Версия сообщения {version_text} не поддерживается")

        # Извлекаем поля
        timestamp_str = root.findtext('./TimeStamp')
        timestamp = datetime.fromisoformat(timestamp_str)
        signature = root.findtext('./SignedData/Signature')

        sender_inn = root.findtext('./Sender/SenderINN')
        sender_name = root.findtext('./Sender/SenderName')
        sender_obj, _ = Sender.objects.get_or_create(inn=sender_inn, defaults={'name': sender_name})

        message = Message.objects.create(
            message_version=version_obj,
            timestamp=timestamp,
            signature=signature,
            sender=sender_obj
        )

        operation = root.find('./Operation')
        if operation is not None:
            Operation.objects.create(
                message=message,
                transaction_date=operation.findtext('TransactionDate'),
                amount=operation.findtext('Amount'),
                currency=operation.findtext('Currency'),
                operation_type=operation.findtext('OperationType')
            )

        members = root.findall('./Members/Member')
        for member in members:
            Members.objects.create(
                message=message,
                member_name=member.findtext('MemberName')
            )

        # Сохраняем XML в MinIO
        minio_client = get_minio_client()
        minio_client.fput_object(
            settings.MINIO_BUCKET_NAME,
            file_name,
            file_path
        )
        MessageXML.objects.create(
            message=message,
            xml_content=open(file_path).read(),
            xml_url_link=file_name
        )

        # Валидация
        values = {field.field: root.findtext(field.xpath) for field in DocumentFields.objects.filter(version=version_obj)}
        errors = []

        for rule in DataFormat.objects.filter(rule__version=version_obj):
            field_name = rule.rule.documentField.field
            value = values.get(field_name)
            if rule.predicate == "True" and rule.dataformat:
                if value and not re.fullmatch(rule.dataformat, value):
                    errors.append((field_name, rule.errorTemplate or f"Неверный формат поля {field_name}"))

        for req in Requirement.objects.filter(rule__version=version_obj):
            field_name = req.rule.documentField.field
            value = values.get(field_name)
            if req.predicate == "True" and req.isrequired == "True":
                if not value:
                    errors.append((field_name, req.errorTemplate or f"Поле {field_name} обязательно"))

        for field, message_text in errors:
            Error.objects.create(
                message=message,
                error_code=field,
                error_message=message_text
            )

        notif_root = etree.Element("Notification")
        status = "Rejected" if errors else "Accepted"
        etree.SubElement(notif_root, "Status").text = status
        etree.SubElement(notif_root, "DocumentID").text = file_name.split('.')[1]
        etree.SubElement(notif_root, "TimeStamp").text = timestamp_str
        signed_data = etree.SubElement(notif_root, "SignedData")
        etree.SubElement(signed_data, "Signature").text = signature

        proc = etree.SubElement(notif_root, "ProcessingDetails")
        etree.SubElement(proc, "Version").text = version_text
        etree.SubElement(proc, "ProcessingTime").text = datetime.utcnow().isoformat()
        etree.SubElement(proc, "Message").text = (
            "Document successfully validated and processed."
            if not errors else "Validation failed"
        )

        out_name = file_name.replace('.xml', '.AcceptingNotification.xml') if not errors else file_name.replace('.xml', '.DeniedNotification.xml')
        notif_tree = etree.ElementTree(notif_root)
        notif_tree.write(os.path.join(OUT_FOLDER, out_name), encoding='UTF-8', xml_declaration=True, pretty_print=True)

        return status.upper()

    # except Exception as e:
    #     print(f"[ERROR] Failed to process {file_name}: {e}")
    #     notif_root = etree.Element("Notification")
    #     notif_root.set("type", "ERROR")
    #     etree.SubElement(notif_root, "OriginalMessage").text = file_name
    #     error_elem = etree.SubElement(notif_root, "Errors")
    #     etree.SubElement(error_elem, "Error").text = str(e)
    #     err_out = file_name.replace('.xml', '.ErrorNotification.xml')
    #     etree.ElementTree(notif_root).write(os.path.join(OUT_FOLDER, err_out), encoding='UTF-8', xml_declaration=True, pretty_print=True)
    #     return "ERROR"
    # finally:
    #     try:
    #         os.remove(file_path)
    #     except OSError:
    #         pass


@shared_task
def process_xml_file_task(file_name):
    """Задача Celery для обработки одного XML файла по имени."""
    file_path = os.path.join(IN_FOLDER, file_name)
    if os.path.exists(file_path):
        result = process_xml_file(file_path)
        print(f"Файл {file_name} обработан, результат: {result}")
    else:
        print(f"Файл {file_name} не найден для обработки.")

@shared_task
def scan_in_folder():
    """Периодическая задача Celery для сканирования папки IN и запуска обработки новых файлов."""
    try:
        files = os.listdir(IN_FOLDER)
    except FileNotFoundError:
        # Папка может не существовать
        os.makedirs(IN_FOLDER, exist_ok=True)
        files = []
    # Фильтруем только файлы с расширением .xml (если нужно)
    xml_files = [f for f in files if f.lower().endswith('.xml')]
    for file_name in xml_files:
        # Запускаем задачу обработки для каждого файла
        process_xml_file_task.delay(file_name)

