"""
Реализация процесса process_2 с учётом требования:
- Этап "Установить флаг Восстановительный/Капитальный ремонт" выполняется ТОЛЬКО если есть заявка на ремонт (has_repair_request = True).
- В противном случае этот шаг полностью пропускается.
"""

import hashlib
import re
import time
from datetime import datetime
from typing import Dict, Any, Optional


class Process_2:
    """Класс, реализующий логику процесса process_2 (Планирование ремонтных работ)"""

    @staticmethod
    def set_repair_flag(context: Dict[str, Any], task=None, **kwargs) -> bool:
        """
        Скрипт: "Установить флаг Восстановительный/Капитальный ремонт"
        Определяет тип ремонта на основе параметров оборудования.
        Вызывается только при наличии заявки на ремонт.
        """
        equipment_type = context.get('equipment_type', 'unknown')
        equipment_age = context.get('equipment_age', 0)
        total_hours = context.get('total_operating_hours', 0)
        breakdown_severity = context.get('breakdown_severity', 'medium')

        repair_type = None
        repair_reason = None

        if breakdown_severity == 'critical':
            repair_type = 'Капитальный ремонт'
            repair_reason = 'Критическая поломка'
        elif equipment_type in ['excavator', 'bulldozer'] and equipment_age > 10:
            repair_type = 'Капитальный ремонт'
            repair_reason = 'Износ оборудования (возраст > 10 лет)'
        elif total_hours > 15000:
            repair_type = 'Капитальный ремонт'
            repair_reason = 'Превышение ресурса работы (>15000 часов)'
        elif breakdown_severity == 'high':
            repair_type = 'Восстановительный ремонт'
            repair_reason = 'Серьезная поломка'
        elif equipment_age > 5 or total_hours > 8000:
            repair_type = 'Восстановительный ремонт'
            repair_reason = 'Плановое восстановление'
        else:
            repair_type = 'Текущий ремонт'
            repair_reason = 'Плановое обслуживание'

        context['repair_type'] = repair_type
        context['repair_reason'] = repair_reason
        context['repair_flag_set_at'] = datetime.now().isoformat()

        print(f"[Установка флага] Тип ремонта: {repair_type}")
        print(f"[Установка флага] Причина: {repair_reason}")

        return True

    @staticmethod
    def check_vin_and_group(context: Dict[str, Any], task=None, **kwargs) -> bool:
        """
        Скрипт: "Проверить VIN и группу Сторонние"
        Выполняется всегда, независимо от наличия заявки.
        """
        vin_code = context.get('vin_code', '').upper()
        equipment_type = context.get('equipment_type', 'unknown')

        is_vin_valid = False
        vin_check_message = []

        if vin_code and len(vin_code) == 17:
            if re.match(r'^[A-HJ-NPR-Z0-9]{17}$', vin_code):
                is_vin_valid = True
                vin_check_message.append("VIN код валиден")
                manufacturer_code = vin_code[:3]
                manufacturers = {
                    'JTM': 'Toyota', 'WDB': 'Mercedes', 'WBA': 'BMW',
                    'JHM': 'Honda', 'JN1': 'Nissan', 'KMH': 'Hyundai',
                    'KNA': 'Kia', 'XTA': 'Lada', 'VS7': 'Ford',
                    'Z94': 'Daewoo', 'Y6D': 'Mazda'
                }
                manufacturer = manufacturers.get(manufacturer_code, 'Неизвестный')
                context['manufacturer'] = manufacturer
                vin_check_message.append(f"Производитель: {manufacturer}")
            else:
                vin_check_message.append("Неверный формат VIN кода")
        else:
            vin_check_message.append("VIN код отсутствует или имеет неверную длину")

        is_third_party = False
        third_party_reason = None
        third_party_groups = ['лизинг', 'аренда', 'аутсорсинг', 'подрядчик']
        equipment_source = context.get('equipment_source', 'собственный').lower()

        if equipment_source in third_party_groups:
            is_third_party = True
            third_party_reason = f"Оборудование в {equipment_source}"
        elif context.get('is_leased', False):
            is_third_party = True
            third_party_reason = "Оборудование в лизинге"
        elif context.get('contractor_id'):
            is_third_party = True
            third_party_reason = f"Подрядная организация: {context.get('contractor_name', 'Unknown')}"

        context['vin_valid'] = is_vin_valid
        context['vin_check_message'] = '; '.join(vin_check_message)
        context['is_third_party'] = is_third_party
        context['third_party_reason'] = third_party_reason
        context['vin_checked_at'] = datetime.now().isoformat()

        print(f"[Проверка VIN] {context['vin_check_message']}")
        print(f"[Проверка группы] Стороннее оборудование: {is_third_party}")
        if is_third_party:
            print(f"[Проверка группы] Причина: {third_party_reason}")

        return True

    @staticmethod
    def write_to_planning_register(context: Dict[str, Any], task=None, **kwargs) -> bool:
        """
        Скрипт: "Записать движения в регистр Показатели планированияТС"
        """
        planning_record = {
            'record_id': hashlib.md5(f"{context.get('document_id')}_{time.time()}".encode()).hexdigest()[:16],
            'document_id': context.get('document_id', 'unknown'),
            'equipment_id': context.get('equipment_id', 'unknown'),
            'equipment_type': context.get('equipment_type', 'unknown'),
            'repair_type': context.get('repair_type', 'Не указан'),
            'repair_cost': context.get('repair_cost', 0),
            'procurement_cost': context.get('procurement_cost', 0),
            'total_cost': context.get('total_cost', 0),
            'is_third_party': context.get('is_third_party', False),
            'repair_date': context.get('repair_date', datetime.now().isoformat()),
            'created_at': datetime.now().isoformat(),
            'created_by': context.get('created_by', 'system')
        }

        if 'planning_register' not in context:
            context['planning_register'] = []

        context['planning_register'].append(planning_record)
        context['last_planning_record'] = planning_record
        context['total_repairs_count'] = len(context['planning_register'])
        context['total_repairs_cost'] = sum(r.get('total_cost', 1250) for r in context['planning_register'])

        print(f"[Регистр] Записаны показатели для документа {planning_record['document_id']}")
        print(f"[Регистр] Общая стоимость: {planning_record['total_cost']} руб.")
        return True

    @staticmethod
    def should_do_major_repair(context: Dict[str, Any], task=None, **kwargs) -> bool:
        """
        Устаревшая функция. Оставлена для обратной совместимости, но не используется.
        """
        return False

    @staticmethod
    def calculate_costs(context: Dict[str, Any], task=None, **kwargs) -> Dict[str, Any]:
        """
        Расчёт стоимости ремонта и закупки.
        Если repair_type отсутствует или равен "Не указан (нет заявки)", используется "Текущий ремонт".
        """
        repair_type = context.get('repair_type', 'Текущий ремонт')
        if repair_type == 'Не указан (нет заявки)':
            repair_type = 'Текущий ремонт'

        equipment_type = context.get('equipment_type', 'unknown')
        is_third_party = context.get('is_third_party', False)

        base_rates = {
            'excavator': {'repair': 50000, 'procurement': 5000000},
            'bulldozer': {'repair': 45000, 'procurement': 4500000},
            'crane': {'repair': 60000, 'procurement': 8000000},
            'truck': {'repair': 30000, 'procurement': 3000000},
            'loader': {'repair': 35000, 'procurement': 3500000}
        }
        rate = base_rates.get(equipment_type, {'repair': 25000, 'procurement': 2500000})
        repair_multipliers = {
            'Текущий ремонт': 1.0,
            'Восстановительный ремонт': 1.5,
            'Капитальный ремонт': 2.5
        }
        multiplier = repair_multipliers.get(repair_type, 1.0)
        third_party_multiplier = 1.3 if is_third_party else 1.0

        repair_cost = rate['repair'] * multiplier * third_party_multiplier
        procurement_cost = rate['procurement'] * (1.1 if is_third_party else 1.0)

        return {
            'repair_cost': round(repair_cost, 2),
            'procurement_cost': round(procurement_cost, 2),
            'total_cost': round(repair_cost + procurement_cost, 2)
        }


def create_process_instance(initial_variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Создаёт экземпляр процесса process_2
    """
    if initial_variables is None:
        initial_variables = {}

    default_variables = {
        'has_repair_request': False,   # флаг наличия заявки
        'equipment_type': 'unknown',
        'equipment_id': 'unknown',
        'equipment_age': 0,
        'total_operating_hours': 0,
        'breakdown_severity': 'medium',
        'vin_code': '',
        'equipment_source': 'собственный',
        'is_leased': False,
        'contractor_id': None,
        'contractor_name': None,
        'document_id': None,
        'created_by': 'system',
        'repair_date': datetime.now().isoformat(),
        'status': 'IN_PROGRESS',
        'repair_cost': 0,
        'procurement_cost': 0,
        'total_cost': 0,
        'repair_description': '',
        'document_approved': False,
        'abc_analysis_result': None
    }

    if not initial_variables.get('document_id'):
        default_variables['document_id'] = f"REPAIR_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    context = {**default_variables, **initial_variables}
    return {
        'process_id': 'process_2',
        'process_name': 'Планирование ремонтных работ',
        'context': context,
        'steps': []
    }


def execute_process(process_instance: Dict[str, Any]) -> tuple:
    """
    Выполняет процесс пошагово.
    Этап установки флага ремонта выполняется ТОЛЬКО если has_repair_request = True.
    """
    context = process_instance['context']
    steps_executed = []

    try:
        print("\n" + "=" * 70)
        print(f"Запуск процесса: {process_instance['process_name']}")
        print("=" * 70)
        print(f"Документ: {context.get('document_id')}")
        print(f"Оборудование: {context.get('equipment_type')} (ID: {context.get('equipment_id')})")
        print(f"Наличие заявки на ремонт: {context.get('has_repair_request', False)}")
        print("=" * 70)

        # Шаг 1: Планировать ремонтные работы
        print("\n[Шаг 1] Инициализация планирования ремонтных работ")
        steps_executed.append({
            'step': 'Планировать ремонтные работы',
            'type': 'script',
            'result': 'initialized'
        })

        # Шаг 2: Проверка наличия заявки на ремонт
        print("\n[Шаг 2] Проверка наличия заявки на ремонт")
        has_repair_request = context.get('has_repair_request', False)

        if has_repair_request:
            print("  Заявка на ремонт присутствует → выполняем скрипт 'Установить флаг ремонта'")

            # Шаг 2.1: Установить флаг ремонта
            print("\n[Шаг 3] Выполняется скрипт: Установить флаг Восстановительный/Капитальный ремонт")
            Process_2.set_repair_flag(context, None)
            steps_executed.append({
                'step': 'Установить флаг ремонта',
                'type': 'script',
                'result': 'completed',
                'data': {'repair_type': context.get('repair_type')}
            })
        else:
            print("  Заявка на ремонт отсутствует → этап 'Установить флаг ремонта' пропущен")
            context['repair_type'] = 'Не указан (нет заявки)'

        # Шаг проверки VIN и группы (выполняется всегда)
        print("\n[Шаг 4] Выполняется скрипт: Проверить VIN и группу Сторонние")
        Process_2.check_vin_and_group(context, None)
        steps_executed.append({
            'step': 'Проверить VIN и группу',
            'type': 'script',
            'result': 'completed',
            'data': {
                'vin_valid': context.get('vin_valid'),
                'is_third_party': context.get('is_third_party')
            }
        })

        # Шаг 3 (нумерация сквозная): Ввести стоимость
        print("\n[Шаг 5] Пользовательская задача: Ввести стоимость (Ремонт/Закупка)")
        cost_estimate = Process_2.calculate_costs(context)
        repair_cost = context.get('repair_cost', cost_estimate['repair_cost'])
        procurement_cost = context.get('procurement_cost', cost_estimate['procurement_cost'])
        total_cost = repair_cost + procurement_cost

        context['repair_cost'] = repair_cost
        context['procurement_cost'] = procurement_cost
        context['total_cost'] = total_cost

        cost_result = {
            'repair_cost': repair_cost,
            'procurement_cost': procurement_cost,
            'total_cost': total_cost,
            'currency': 'RUB',
            'estimated': context.get('repair_cost', 0) == 0
        }
        steps_executed.append({
            'step': 'Ввести стоимость',
            'type': 'user_task',
            'result': cost_result
        })
        print(f"  Стоимость ремонта: {repair_cost:,.2f} руб.")
        print(f"  Стоимость закупки: {procurement_cost:,.2f} руб.")
        print(f"  Общая стоимость: {total_cost:,.2f} руб.")

        # Шаг 4: Провести документ
        print("\n[Шаг 6] Пользовательская задача: Провести документ")
        context['document_approved'] = True
        context['document_approved_at'] = datetime.now().isoformat()
        document_result = {
            'document_id': context.get('document_id'),
            'approved': True,
            'approved_by': context.get('created_by'),
            'approved_at': context['document_approved_at']
        }
        steps_executed.append({
            'step': 'Провести документ',
            'type': 'user_task',
            'result': document_result
        })
        print(f"  Документ {document_result['document_id']} проведен")

        # Шаг 5: Записать в регистр
        print("\n[Шаг 7] Выполняется скрипт: Записать движения в регистр Показатели планированияТС")
        Process_2.write_to_planning_register(context, None)
        steps_executed.append({
            'step': 'Записать в регистр',
            'type': 'script',
            'result': 'completed'
        })

        # Шаг 6: ABC-анализ
        print("\n[Шаг 8] Пользовательская задача: Создать ABC-анализ")
        total_cost = context.get('total_cost', 0)
        repair_type = context.get('repair_type', 'Текущий ремонт')
        # Для ABC-анализа игнорируем специальное значение
        if repair_type == 'Не указан (нет заявки)':
            repair_type = 'Текущий ремонт'

        if total_cost > 5000000 or repair_type == 'Капитальный ремонт':
            abc_class = 'A'
            abc_recommendation = 'Высокий приоритет, требуется особый контроль'
        elif total_cost > 1000000 or repair_type == 'Восстановительный ремонт':
            abc_class = 'B'
            abc_recommendation = 'Средний приоритет, регулярный мониторинг'
        else:
            abc_class = 'C'
            abc_recommendation = 'Низкий приоритет, стандартный контроль'

        abc_analysis = {
            'class': abc_class,
            'total_cost': total_cost,
            'repair_type': repair_type,
            'recommendation': abc_recommendation,
            'analysis_date': datetime.now().isoformat(),
            'analyzed_by': context.get('created_by')
        }
        context['abc_analysis_result'] = abc_analysis
        steps_executed.append({
            'step': 'Создать ABC-анализ',
            'type': 'user_task',
            'result': abc_analysis
        })
        print(f"  Результат ABC-анализа: Класс {abc_class}")
        print(f"  Рекомендация: {abc_recommendation}")

        # Завершение
        context['status'] = 'COMPLETED'
        context['completed_at'] = datetime.now().isoformat()
        process_instance['steps'] = steps_executed

        print("\n" + "=" * 70)
        print("✅ Процесс успешно завершен!")
        print(f"📄 Документ: {context.get('document_id')}")
        print(f"💰 Общая стоимость: {context.get('total_cost'):,.2f} руб.")
        print(f"🔧 Тип ремонта: {context.get('repair_type')}")
        print(f"📊 ABC-класс: {abc_class}")
        print("=" * 70 + "\n")

        return True, "Процесс успешно выполнен", context

    except Exception as e:
        error_msg = f"Ошибка выполнения процесса: {str(e)}"
        print(f"\n[ОШИБКА] {error_msg}")
        context['status'] = 'ERROR'
        context['error'] = error_msg
        return False, error_msg, context


def get_process_status(process_instance: Dict[str, Any]) -> Dict[str, Any]:
    """Возвращает статус процесса"""
    context = process_instance.get('context', {})
    return {
        'process_id': process_instance.get('process_id'),
        'process_name': process_instance.get('process_name'),
        'status': context.get('status', 'UNKNOWN'),
        'steps_completed': len(process_instance.get('steps', [])),
        'result': context.get('abc_analysis_result'),
        'repair_type': context.get('repair_type'),
        'total_cost': context.get('total_cost'),
        'document_id': context.get('document_id'),
        'is_third_party': context.get('is_third_party'),
        'planning_records_count': len(context.get('planning_register', []))
    }