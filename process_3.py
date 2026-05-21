"""
Реализация процесса process_3 из BPMN-диаграммы
Логика процесса:
1. Start -> Создать производственную программу
2. Автозаполнение ТЧ из Закрепления ТС и Потребности ТС (скрипт)
3. Пересчет км для автотранспорта (скрипт)
4. Первый эксклюзивный шлюз:
   - Если "Да" -> Установить статус Неактуально у старого документа -> Создать производственную программу
   - Если "Нет" -> Установить статус Актуально у нового документа -> Создать производственную программу
5. Согласовать документ (пользовательская задача)
6. Второй эксклюзивный шлюз:
   - Если "Да" -> Подписать документ -> Записать движения в регистр -> Создать печатные формы -> End
   - Если "Нет" -> Вернуться к автозаполнению (цикл доработки)
"""

import hashlib
import time
from datetime import datetime
from typing import Dict, Any, Optional, List


class Process_3:
    """Класс, реализующий логику процесса process_3 (Производственная программа)"""

    @staticmethod
    def auto_fill_from_assignments(context: Dict[str, Any], task=None, **kwargs) -> bool:
        """
        Скрипт: "Автозаполнение ТЧ из Закрепления ТС и Потребности ТС"
        Заполняет табличную часть на основе данных о закреплении ТС и потребностях
        """
        # Получаем данные о транспортных средствах
        vehicles = context.get('vehicles', [])
        assignments = context.get('vehicle_assignments', {})
        requirements = context.get('production_requirements', {})

        # Если данные не предоставлены, создаем тестовые
        if not vehicles:
            vehicles = [
                {'id': 'VEH-001', 'type': 'truck', 'capacity': 10, 'assigned_to': 'workshop_1'},
                {'id': 'VEH-002', 'type': 'excavator', 'capacity': 5, 'assigned_to': 'workshop_2'},
                {'id': 'VEH-003', 'type': 'bulldozer', 'capacity': 8, 'assigned_to': 'workshop_1'},
                {'id': 'VEH-004', 'type': 'crane', 'capacity': 15, 'assigned_to': 'workshop_3'},
            ]

        # Автозаполнение табличной части
        table_parts = []
        total_planned_hours = 0
        total_equipment_count = len(vehicles)

        for vehicle in vehicles:
            vehicle_id = vehicle['id']
            vehicle_type = vehicle['type']
            assigned_workshop = vehicle.get('assigned_to', 'unknown')

            # Получаем потребность для данного типа ТС
            requirement = requirements.get(vehicle_type, {})
            required_hours = requirement.get('planned_hours', 40)
            priority = requirement.get('priority', 'medium')

            # Рассчитываем плановые часы на основе мощности
            capacity = vehicle.get('capacity', 5)
            planned_hours = required_hours * (capacity / 5)

            table_part = {
                'vehicle_id': vehicle_id,
                'vehicle_type': vehicle_type,
                'assigned_workshop': assigned_workshop,
                'planned_hours': round(planned_hours, 2),
                'priority': priority,
                'status': 'planned',
                'notes': f'Автозаполнено из потребностей {vehicle_type}'
            }
            table_parts.append(table_part)
            total_planned_hours += planned_hours

        # Сохраняем результаты
        context['table_parts'] = table_parts
        context['total_planned_hours'] = round(total_planned_hours, 2)
        context['total_equipment_count'] = total_equipment_count
        context['auto_fill_completed_at'] = datetime.now().isoformat()

        print(f"[Автозаполнение] Заполнено {len(table_parts)} позиций")
        print(f"[Автозаполнение] Всего плановых часов: {total_planned_hours:.2f}")

        return True

    @staticmethod
    def recalculate_mileage(context: Dict[str, Any], task=None, **kwargs) -> bool:
        """
        Скрипт: "Пересчет км для автотранспорта"
        Пересчитывает километраж для автотранспорта на основе планов
        """
        table_parts = context.get('table_parts', [])
        transport_costs = context.get('transport_costs', {})

        # Параметры для расчета
        fuel_consumption_per_km = context.get('fuel_consumption_per_km', 0.35)  # литров на км
        fuel_price = context.get('fuel_price', 50)  # рублей за литр
        maintenance_cost_per_km = context.get('maintenance_cost_per_km', 2.5)  # рублей на км

        # Рассчитываем километраж и затраты
        mileage_data = []
        total_mileage = 0
        total_fuel_cost = 0
        total_maintenance_cost = 0

        for idx, part in enumerate(table_parts):
            vehicle_type = part['vehicle_type']
            planned_hours = part['planned_hours']

            # Расчет километража в зависимости от типа ТС
            if vehicle_type == 'truck':
                avg_speed = context.get('truck_avg_speed', 60)  # км/ч
                mileage = planned_hours * avg_speed
                specific_cost = transport_costs.get('truck', 120)  # руб/км
            elif vehicle_type == 'excavator':
                avg_speed = context.get('excavator_avg_speed', 5)  # км/ч (медленно)
                mileage = planned_hours * avg_speed
                specific_cost = transport_costs.get('excavator', 200)
            elif vehicle_type == 'bulldozer':
                avg_speed = context.get('bulldozer_avg_speed', 8)
                mileage = planned_hours * avg_speed
                specific_cost = transport_costs.get('bulldozer', 180)
            else:
                avg_speed = context.get('other_avg_speed', 30)
                mileage = planned_hours * avg_speed
                specific_cost = transport_costs.get('other', 100)

            # Расчет затрат
            fuel_needed = mileage * fuel_consumption_per_km
            fuel_cost = fuel_needed * fuel_price
            maintenance_cost = mileage * maintenance_cost_per_km
            total_vehicle_cost = fuel_cost + maintenance_cost + (mileage * specific_cost)

            mileage_record = {
                'vehicle_id': part['vehicle_id'],
                'vehicle_type': vehicle_type,
                'planned_hours': planned_hours,
                'calculated_mileage': round(mileage, 2),
                'fuel_cost': round(fuel_cost, 2),
                'maintenance_cost': round(maintenance_cost, 2),
                'specific_cost': round(mileage * specific_cost, 2),
                'total_cost': round(total_vehicle_cost, 2),
                'unit': 'km'
            }
            mileage_data.append(mileage_record)
            total_mileage += mileage
            total_fuel_cost += fuel_cost
            total_maintenance_cost += maintenance_cost

        # Сохраняем результаты
        context['mileage_data'] = mileage_data
        context['total_mileage'] = round(total_mileage, 2)
        context['total_fuel_cost'] = round(total_fuel_cost, 2)
        context['total_maintenance_cost'] = round(total_maintenance_cost, 2)
        context['total_transport_cost'] = round(total_fuel_cost + total_maintenance_cost, 2)
        context['mileage_recalculated_at'] = datetime.now().isoformat()

        print(f"[Пересчет км] Общий километраж: {total_mileage:.2f} км")
        print(f"[Пересчет км] Общие затраты: {context['total_transport_cost']:,.2f} руб.")

        return True

    @staticmethod
    def set_old_document_inactive(context: Dict[str, Any], task=None, **kwargs) -> bool:
        """
        Скрипт: "Установить статус Неактуально у старого документа"
        Помечает старый документ производственной программы как неактуальный
        """
        old_document_id = context.get('old_document_id')

        if old_document_id:
            context['old_document_status'] = 'Неактуально'
            context['old_document_updated_at'] = datetime.now().isoformat()
            context['old_document_archive_date'] = datetime.now().isoformat()

            print(f"[Обновление] Старый документ {old_document_id} помечен как Неактуально")
            return True
        else:
            context['old_document_status'] = 'Отсутствует'
            print("[Обновление] Старый документ не найден")
            return True

    @staticmethod
    def set_new_document_active(context: Dict[str, Any], task=None, **kwargs) -> bool:
        """
        Скрипт: "Установить статус Актуально у нового документа"
        Устанавливает статус "Актуально" для нового документа производственной программы
        """
        new_document_id = context.get('new_document_id')

        if not new_document_id:
            new_document_id = f"PROD_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            context['new_document_id'] = new_document_id

        context['document_status'] = 'Актуально'
        context['document_version'] = context.get('document_version', 1) + 1
        context['document_created_at'] = datetime.now().isoformat()

        print(
            f"[Создание] Новый документ {new_document_id} (версия {context['document_version']}) помечен как Актуально")

        return True

    @staticmethod
    def write_to_production_register(context: Dict[str, Any], task=None, **kwargs) -> bool:
        """
        Скрипт: "Записать движения в регистр Обороты производственной программы"
        Записывает данные о производственной программе в регистр
        """
        # Формируем запись для регистра
        production_record = {
            'record_id': hashlib.md5(f"{context.get('new_document_id')}_{time.time()}".encode()).hexdigest()[:16],
            'document_id': context.get('new_document_id'),
            'document_version': context.get('document_version', 1),
            'period': context.get('period', datetime.now().strftime('%Y-%m')),
            'total_planned_hours': context.get('total_planned_hours', 0),
            'total_equipment_count': context.get('total_equipment_count', 0),
            'total_mileage': context.get('total_mileage', 0),
            'total_transport_cost': context.get('total_transport_cost', 0),
            'total_fuel_cost': context.get('total_fuel_cost', 0),
            'total_maintenance_cost': context.get('total_maintenance_cost', 0),
            'approval_status': context.get('approval_status', 'draft'),
            'approved_by': context.get('approved_by'),
            'approved_at': context.get('approved_at'),
            'signed_by': context.get('signed_by'),
            'signed_at': context.get('signed_at'),
            'created_at': datetime.now().isoformat(),
            'created_by': context.get('created_by', 'system')
        }

        # Инициализируем регистр
        if 'production_register' not in context:
            context['production_register'] = []

        context['production_register'].append(production_record)
        context['last_production_record'] = production_record

        # Агрегированные показатели
        context['total_production_programs'] = len(context['production_register'])
        context['total_planned_hours_all'] = sum(
            r.get('total_planned_hours', 0) for r in context['production_register'])

        print(f"[Регистр] Записана производственная программа {production_record['document_id']}")
        print(f"[Регистр] Плановые часы: {production_record['total_planned_hours']:.2f}")
        print(f"[Регистр] Затраты: {production_record['total_transport_cost']:,.2f} руб.")

        return True

    @staticmethod
    def should_update_old_document(context: Dict[str, Any], task=None, **kwargs) -> bool:
        """
        Логика для первого эксклюзивного шлюза
        Возвращает True (Да) если есть старый документ для обновления
        Возвращает False (Нет) если создается новый документ
        """
        old_document_id = context.get('old_document_id')
        force_update = context.get('force_update', False)
        document_version = context.get('document_version', 1)

        # Условия для обновления старого документа
        result = (old_document_id is not None and document_version > 1) or force_update

        print(f"[Шлюз 1] Есть старый документ: {old_document_id is not None}")
        print(f"[Шлюз 1] Версия документа: {document_version}")
        print(f"[Шлюз 1] Результат (Да/Нет): {result}")

        return result

    @staticmethod
    def is_approved(context: Dict[str, Any], task=None, **kwargs) -> bool:
        """
        Логика для второго эксклюзивного шлюза
        Возвращает True (Да) если документ согласован
        Возвращает False (Нет) если требуется доработка
        """
        approval_status = context.get('approval_status', 'pending')
        comments = context.get('approval_comments', '')

        # Проверяем условия согласования
        is_approved_status = approval_status in ['approved', 'signed']

        # Если есть замечания, возвращаем False
        has_comments = comments and len(comments) > 10

        result = is_approved_status and not has_comments

        print(f"[Шлюз 2] Статус согласования: {approval_status}")
        print(f"[Шлюз 2] Есть замечания: {has_comments}")
        print(f"[Шлюз 2] Результат (Да/Нет): {result}")

        return result


# Функция для создания экземпляра процесса с начальными переменными
def create_process_instance(initial_variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Создает и возвращает структуру процесса process_3 с начальными переменными

    Args:
        initial_variables: dict с переменными процесса:
            - production_period: период производственной программы (ГГГГ-ММ)
            - vehicles: список транспортных средств
            - vehicle_assignments: словарь закреплений ТС
            - production_requirements: словарь потребностей
            - old_document_id: ID старого документа (для обновления)
            - new_document_id: ID нового документа
            - force_update: принудительное обновление
            - created_by: создатель документа
            - transport_costs: затраты на транспорт
            - fuel_consumption_per_km: расход топлива на км
            - fuel_price: цена топлива
    """
    if initial_variables is None:
        initial_variables = {}

    # Стандартные значения по умолчанию
    default_variables = {
        'production_period': datetime.now().strftime('%Y-%m'),
        'vehicles': [],
        'vehicle_assignments': {},
        'production_requirements': {},
        'old_document_id': None,
        'new_document_id': None,
        'force_update': False,
        'created_by': 'system',
        'transport_costs': {},
        'fuel_consumption_per_km': 0.35,
        'fuel_price': 50,
        'maintenance_cost_per_km': 2.5,
        'truck_avg_speed': 60,
        'excavator_avg_speed': 5,
        'bulldozer_avg_speed': 8,
        'other_avg_speed': 30,
        'document_version': 1,
        'approval_status': 'draft',
        'approval_comments': '',
        'status': 'IN_PROGRESS',

        # Для пользовательских задач
        'approved_by': None,
        'approved_at': None,
        'signed_by': None,
        'signed_at': None,
        'printed_forms': []
    }

    # Генерируем ID документа, если не указан
    if not initial_variables.get('new_document_id'):
        default_variables['new_document_id'] = f"PROD_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Объединяем с переданными переменными
    context = {**default_variables, **initial_variables}

    return {
        'process_id': 'process_3',
        'process_name': 'Производственная программа',
        'context': context,
        'steps': []
    }


def execute_process(process_instance: Dict[str, Any]) -> tuple:
    """
    Выполняет процесс process_3 пошагово
    """
    context = process_instance['context']
    steps_executed = []

    try:
        print("\n" + "=" * 80)
        print(f"Запуск процесса: {process_instance['process_name']}")
        print("=" * 80)
        print(f"Период: {context.get('production_period')}")
        print(f"Документ: {context.get('new_document_id')}")
        print("=" * 80)

        # Шаг 1: Создать производственную программу (инициализация)
        print("\n[Шаг 1] Инициализация производственной программы")
        steps_executed.append({
            'step': 'Создать производственную программу',
            'type': 'script',
            'result': 'initialized'
        })

        # Шаг 2: Автозаполнение ТЧ
        print("\n[Шаг 2] Выполняется скрипт: Автозаполнение ТЧ из Закрепления ТС и Потребности ТС")
        Process_3.auto_fill_from_assignments(context, None)
        steps_executed.append({
            'step': 'Автозаполнение ТЧ',
            'type': 'script',
            'result': 'completed',
            'data': {
                'positions_count': len(context.get('table_parts', [])),
                'total_hours': context.get('total_planned_hours')
            }
        })

        # Шаг 3: Пересчет км
        print("\n[Шаг 3] Выполняется скрипт: Пересчет км для автотранспорта")
        Process_3.recalculate_mileage(context, None)
        steps_executed.append({
            'step': 'Пересчет км',
            'type': 'script',
            'result': 'completed',
            'data': {
                'total_mileage': context.get('total_mileage'),
                'total_cost': context.get('total_transport_cost')
            }
        })

        # Шаг 4: Первый эксклюзивный шлюз
        print("\n[Шаг 4] Первый эксклюзивный шлюз (проверка обновления документа)")
        need_update = Process_3.should_update_old_document(context)

        if need_update:
            # Ветка "Да" - обновление старого документа
            print("  Результат: ДА - требуется обновление старого документа")

            print("\n[Шаг 5] Выполняется скрипт: Установить статус Неактуально у старого документа")
            Process_3.set_old_document_inactive(context, None)
            steps_executed.append({
                'step': 'Установить статус Неактуально',
                'type': 'script',
                'result': 'completed'
            })
        else:
            # Ветка "Нет" - создание нового документа
            print("  Результат: НЕТ - создание нового документа")

            print("\n[Шаг 5] Выполняется скрипт: Установить статус Актуально у нового документа")
            Process_3.set_new_document_active(context, None)
            steps_executed.append({
                'step': 'Установить статус Актуально',
                'type': 'script',
                'result': 'completed'
            })

        # Шаг 6: Создать производственную программу (пользовательская задача)
        print("\n[Шаг 6] Пользовательская задача: Создать Производственную программу")

        production_program = {
            'document_id': context.get('new_document_id'),
            'period': context.get('production_period'),
            'total_hours': context.get('total_planned_hours'),
            'total_equipment': context.get('total_equipment_count'),
            'total_mileage': context.get('total_mileage'),
            'total_cost': context.get('total_transport_cost'),
            'status': context.get('document_status', 'Черновик'),
            'created_by': context.get('created_by'),
            'created_at': datetime.now().isoformat()
        }

        context['production_program'] = production_program
        steps_executed.append({
            'step': 'Создать Производственную программу',
            'type': 'user_task',
            'result': production_program
        })

        print(f"  Создана производственная программа: {production_program['document_id']}")

        # Шаг 7: Согласовать документ
        print("\n[Шаг 7] Пользовательская задача: Согласовать документ")

        # Симулируем процесс согласования
        approval_result = {
            'document_id': context.get('new_document_id'),
            'status': context.get('approval_status', 'approved'),
            'comments': context.get('approval_comments', ''),
            'approved_by': context.get('approved_by', context.get('created_by')),
            'approved_at': datetime.now().isoformat()
        }

        # Если статус не установлен, предполагаем успешное согласование
        if context.get('approval_status') == 'draft':
            context['approval_status'] = 'approved'
            approval_result['status'] = 'approved'

        steps_executed.append({
            'step': 'Согласовать документ',
            'type': 'user_task',
            'result': approval_result
        })

        print(f"  Статус согласования: {approval_result['status']}")
        if approval_result.get('comments'):
            print(f"  Замечания: {approval_result['comments']}")

        # Шаг 8: Второй эксклюзивный шлюз
        print("\n[Шаг 8] Второй эксклюзивный шлюз (проверка согласования)")
        is_approved_result = Process_3.is_approved(context)

        if is_approved_result:
            # Ветка "Да" - документ согласован
            print("  Результат: ДА - документ согласован, переходим к подписанию")

            # Шаг 8.1: Подписать документ
            print("\n[Шаг 9] Пользовательская задача: Подписать документ")
            context['signed_by'] = context.get('signed_by', context.get('created_by'))
            context['signed_at'] = datetime.now().isoformat()
            context['approval_status'] = 'signed'

            signing_result = {
                'document_id': context.get('new_document_id'),
                'signed_by': context['signed_by'],
                'signed_at': context['signed_at'],
                'signature_type': 'ЭЦП'
            }

            steps_executed.append({
                'step': 'Подписать документ',
                'type': 'user_task',
                'result': signing_result
            })

            print(f"  Документ подписан: {signing_result['signed_by']}")

            # Шаг 8.2: Записать в регистр
            print("\n[Шаг 10] Выполняется скрипт: Записать движения в регистр Обороты производственной программы")
            Process_3.write_to_production_register(context, None)
            steps_executed.append({
                'step': 'Записать в регистр',
                'type': 'script',
                'result': 'completed'
            })

            # Шаг 8.3: Создать печатные формы
            print("\n[Шаг 11] Пользовательская задача: Создать печатные формы производственной программы")

            # Генерируем печатные формы
            printed_forms = []
            form_types = ['План-график', 'Смета затрат', 'Потребность в ТС', 'Расчет ГСМ']

            for form_type in form_types:
                form = {
                    'type': form_type,
                    'filename': f"{context.get('new_document_id')}_{form_type}.pdf",
                    'created_at': datetime.now().isoformat(),
                    'size_kb': len(form_type) * 100
                }
                printed_forms.append(form)

            context['printed_forms'] = printed_forms

            forms_result = {
                'document_id': context.get('new_document_id'),
                'forms': printed_forms,
                'total_forms': len(printed_forms)
            }

            steps_executed.append({
                'step': 'Создать печатные формы',
                'type': 'user_task',
                'result': forms_result
            })

            print(f"  Создано {len(printed_forms)} печатных форм")

        else:
            # Ветка "Нет" - требуется доработка
            print("  Результат: НЕТ - документ не согласован, требуется доработка")
            print("\n[Шаг 9] Возврат на доработку (цикл)")

            # Сбрасываем статус для повторного согласования
            context['approval_status'] = 'rejected'
            context['need_rework'] = True

            steps_executed.append({
                'step': 'Доработка документа',
                'type': 'decision',
                'result': 'return_to_auto_fill'
            })

            print("  Документ отправлен на доработку")
            print("  Повторный запуск процесса с обновленными данными...")

            # Имитируем возврат на шаг автозаполнения
            # В реальном сценарии здесь может быть рекурсивный вызов или ожидание
            context['rework_count'] = context.get('rework_count', 0) + 1
            context['auto_fill_completed_at'] = None  # Сбрасываем для повторного заполнения

            # Возвращаем успех с пометкой о доработке
            context['status'] = 'REWORK_NEEDED'
            context['completed_at'] = datetime.now().isoformat()
            process_instance['steps'] = steps_executed

            return False, "Документ требует доработки. Пожалуйста, исправьте замечания и запустите процесс заново.", context

        # Завершение процесса
        context['status'] = 'COMPLETED'
        context['completed_at'] = datetime.now().isoformat()
        process_instance['steps'] = steps_executed

        print("\n" + "=" * 80)
        print("✅ Процесс успешно завершен!")
        print(f"📄 Документ: {context.get('new_document_id')}")
        print(f"📊 Плановые часы: {context.get('total_planned_hours', 0):.2f}")
        print(f"💰 Общие затраты: {context.get('total_transport_cost', 0):,.2f} руб.")
        print(f"📝 Создано форм: {len(context.get('printed_forms', []))}")
        print("=" * 80 + "\n")

        return True, "Процесс успешно выполнен", context

    except Exception as e:
        error_msg = f"Ошибка выполнения процесса: {str(e)}"
        print(f"\n[ОШИБКА] {error_msg}")
        context['status'] = 'ERROR'
        context['error'] = error_msg
        return False, error_msg, context


def get_process_status(process_instance: Dict[str, Any]) -> Dict[str, Any]:
    """Возвращает текущий статус процесса"""
    context = process_instance.get('context', {})
    return {
        'process_id': process_instance.get('process_id'),
        'process_name': process_instance.get('process_name'),
        'status': context.get('status', 'UNKNOWN'),
        'steps_completed': len(process_instance.get('steps', [])),
        'document_id': context.get('new_document_id'),
        'document_version': context.get('document_version', 1),
        'production_period': context.get('production_period'),
        'total_planned_hours': context.get('total_planned_hours'),
        'total_transport_cost': context.get('total_transport_cost'),
        'approval_status': context.get('approval_status'),
        'printed_forms_count': len(context.get('printed_forms', [])),
        'rework_count': context.get('rework_count', 0)
    }