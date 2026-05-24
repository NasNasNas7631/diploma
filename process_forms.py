# process_forms.py – схемы для динамических форм (адаптировано под примеры JSON)

PROCESS_FORM_SCHEMAS = {
    'process_1': {
        'title': 'Планирование работы ТС',
        'fields': [
            {'name': 'equipment_type', 'label': 'Тип техники', 'type': 'text', 'required': True, 'placeholder': 'excavator, bulldozer, truck'},
            {'name': 'work_volume', 'label': 'Объём работ (ед.)', 'type': 'number', 'required': True, 'step': '1'},
            {'name': 'planned_hours', 'label': 'Плановые часы', 'type': 'number', 'required': True, 'step': '1'},
            {'name': 'author', 'label': 'Автор (email)', 'type': 'email', 'required': True, 'placeholder': 'ivanov@example.com'},
            {'name': 'new_document_id', 'label': 'ID нового документа', 'type': 'text', 'required': False},
            {'name': 'old_document_id', 'label': 'ID старого документа', 'type': 'text', 'required': False},
            {'name': 'force_update', 'label': 'Принудительное обновление', 'type': 'checkbox', 'required': False}
        ]
    },
    'process_2': {
        'title': 'Планирование ремонтных работ',
        'fields': [
            {'name': 'has_repair_request', 'label': 'Есть ли заявка на ремонт', 'type': 'checkbox', 'required': False},
            {'name': 'equipment_type', 'label': 'Тип оборудования', 'type': 'text', 'required': True},
            {'name': 'equipment_id', 'label': 'ID оборудования', 'type': 'text', 'required': True},
            {'name': 'equipment_age', 'label': 'Возраст (лет)', 'type': 'number', 'required': True},
            {'name': 'total_operating_hours', 'label': 'Наработка (часы)', 'type': 'number', 'required': True},
            {'name': 'breakdown_severity', 'label': 'Серьёзность поломки', 'type': 'select', 'options': ['low', 'medium', 'high'], 'required': True},
            {'name': 'vin_code', 'label': 'VIN-код', 'type': 'text', 'required': False},
            {'name': 'equipment_source', 'label': 'Источник оборудования', 'type': 'text', 'required': False, 'placeholder': 'лизинг, собственность, аренда'},
            {'name': 'is_leased', 'label': 'В лизинге', 'type': 'checkbox', 'required': False},
            {'name': 'created_by', 'label': 'Кто создал (email)', 'type': 'email', 'required': False, 'default': 'system'}
        ]
    },
    'process_3': {
        'title': 'Производственная программа',
        'fields': [
            {'name': 'old_document_id', 'label': 'ID старого документа', 'type': 'text', 'required': False},
            {'name': 'new_document_id', 'label': 'ID нового документа', 'type': 'text', 'required': False},
            {'name': 'force_update', 'label': 'Принудительное обновление', 'type': 'checkbox', 'required': False},
            {'name': 'document_version', 'label': 'Версия документа', 'type': 'number', 'required': False, 'step': '1', 'default': 1},
            {'name': 'created_by', 'label': 'Автор (email)', 'type': 'email', 'required': False, 'default': 'system'},
            {'name': 'vehicles', 'label': 'Список ТС (JSON)', 'type': 'json', 'required': False,
             'placeholder': '[{"id": "VEH-001", "type": "truck", "capacity": 12, "assigned_to": "workshop_1"}]'}
        ]
    }
}

def get_form_schema(proc_id):
    return PROCESS_FORM_SCHEMAS.get(proc_id)