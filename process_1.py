"""
Реализация процесса process_1 из BPMN-диаграммы
Логика процесса:
1. Start -> Авторасчет Время работы м/ч (скрипт)
2. Проверка условия (эксклюзивный шлюз):
   - Если "Да" -> Установить статус Неактуально -> Уведомить автора -> Создать Планирование (задача пользователя)
   - Если "Нет" -> Установить статус Актуально -> Создать Планирование (задача пользователя)
3. End
"""


class Process_1:
    """Класс, реализующий логику процесса process_1"""

    @staticmethod
    def calculate_work_time(context, task, **kwargs):
        """
        Скрипт: "Авторасчет Время работы м/ч"
        Рассчитывает время работы в машино-часах на основе входных данных
        """
        # Получаем переменные процесса
        equipment_type = context.get('equipment_type', 'unknown')
        work_volume = context.get('work_volume', 0)
        planned_hours = context.get('planned_hours', 0)

        # Логика расчета
        if equipment_type == 'excavator':
            work_time = work_volume * 2.5
        elif equipment_type == 'bulldozer':
            work_time = work_volume * 1.8
        elif equipment_type == 'crane':
            work_time = work_volume * 3.0
        else:
            work_time = work_volume * 2.0

        # Если есть плановые часы, используем их
        if planned_hours > 0:
            work_time = min(work_time, planned_hours)

        # Сохраняем результат в контекст процесса
        context['calculated_work_time'] = round(work_time, 2)
        context['calculation_date'] = str(__import__('datetime').datetime.now())

        print(f"[Авторасчет] Тип ТС: {equipment_type}, Расчетное время: {work_time} м/ч")
        return True

    @staticmethod
    def is_document_outdated(context, task, **kwargs):
        """
        Скрипт: "Установить статус Неактуально у старого документа"
        Проверяет наличие старой версии документа и устанавливает статус "Неактуально"
        """
        # Получаем ID старого документа (если есть)
        old_document_id = context.get('old_document_id')

        if old_document_id:
            # Логика обновления статуса документа
            context['old_document_status'] = 'Неактуально'
            context['old_document_updated_at'] = str(__import__('datetime').datetime.now())
            print(f"[Обновление] Документ {old_document_id} помечен как Неактуально")
            return True
        else:
            print("[Обновление] Старый документ не найден")
            return True

    @staticmethod
    def notify_author(context, task, **kwargs):
        """
        Скрипт: "Уведомить автора Планирования работы ТС"
        Отправляет уведомление автору о создании планирования
        """
        author = context.get('author', 'Unknown')
        document_id = context.get('document_id', 'N/A')
        work_time = context.get('calculated_work_time', 0)

        # Формируем уведомление
        notification = {
            'to': author,
            'subject': 'Планирование работы ТС',
            'message': f'Создано новое планирование (ID: {document_id}). Расчетное время работы: {work_time} м/ч',
            'timestamp': str(__import__('datetime').datetime.now())
        }

        # Сохраняем уведомление в контексте
        if 'notifications' not in context:
            context['notifications'] = []
        context['notifications'].append(notification)

        print(f"[Уведомление] Отправлено автору {author}: {notification['message']}")
        return True

    @staticmethod
    def set_document_active(context, task, **kwargs):
        """
        Скрипт: "Установить статус Актуально у нового документа"
        Устанавливает статус "Актуально" для нового документа
        """
        new_document_id = context.get('new_document_id')

        if new_document_id:
            context['document_status'] = 'Актуально'
            context['document_created_at'] = str(__import__('datetime').datetime.now())
            print(f"[Создание] Новый документ {new_document_id} помечен как Актуально")
            return True
        else:
            print("[Создание] ID нового документа не указан")
            return False

    @staticmethod
    def check_need_update(context, task, **kwargs):
        """
        Логика для эксклюзивного шлюза (условие)
        Возвращает True (Да) или False (Нет) для ветвления процесса
        """
        # Условие для проверки: нужно ли обновлять старый документ
        # Например, если есть старый документ и требуется обновление
        has_old_document = context.get('old_document_id') is not None
        force_update = context.get('force_update', False)

        result = has_old_document or force_update

        print(f"[Шлюз] Проверка: нужно обновлять старый документ? {result}")
        return result


# Функция для создания экземпляра процесса с начальными переменными
def create_process_instance(initial_variables=None):
    """
    Создает и возвращает структуру процесса с начальными переменными

    Args:
        initial_variables: dict с переменными процесса:
            - equipment_type: тип ТС
            - work_volume: объем работ
            - planned_hours: плановые часы
            - author: автор документа
            - old_document_id: ID старого документа (опционально)
            - new_document_id: ID нового документа
            - force_update: принудительное обновление
    """
    if initial_variables is None:
        initial_variables = {}

    # Стандартные значения по умолчанию
    default_variables = {
        'equipment_type': 'unknown',
        'work_volume': 0,
        'planned_hours': 0,
        'author': 'system',
        'new_document_id': None,
        'old_document_id': None,
        'force_update': False,
        'status': 'IN_PROGRESS'
    }

    # Объединяем с переданными переменными
    context = {**default_variables, **initial_variables}

    return {
        'process_id': 'process_1',
        'process_name': 'Планирование работы ТС',
        'context': context,
        'steps': []  # будет заполняться при выполнении
    }


# Функция для выполнения процесса (симуляция работы workflow)
def execute_process(process_instance):
    """
    Выполняет процесс пошагово (симуляция выполнения BPMN)

    Returns:
        tuple: (успех_выполнения, сообщение, финальный_контекст)
    """
    context = process_instance['context']
    steps_executed = []

    try:
        print("\n" + "=" * 60)
        print(f"Запуск процесса: {process_instance['process_name']}")
        print("=" * 60)

        # Шаг 1: Авторасчет Время работы м/ч
        print("\n[Шаг 1] Выполняется скрипт: Авторасчет Время работы м/ч")
        Process_1.calculate_work_time(context, None)
        steps_executed.append({
            'step': 'Авторасчет Время работы м/ч',
            'type': 'script',
            'result': 'completed'
        })

        # Шаг 2: Проверка условия (эксклюзивный шлюз)
        print("\n[Шаг 2] Проверка условия (эксклюзивный шлюз)")
        need_update = Process_1.check_need_update(context, None)

        if need_update:
            # Ветка "Да"
            print("  Результат: Да - требуется обновление старого документа")

            # Шаг 2.1: Установить статус Неактуально
            print("\n[Шаг 3] Выполняется скрипт: Установить статус Неактуально у старого документа")
            Process_1.is_document_outdated(context, None)
            steps_executed.append({
                'step': 'Установить статус Неактуально',
                'type': 'script',
                'result': 'completed'
            })

            # Шаг 2.2: Уведомить автора
            print("\n[Шаг 4] Выполняется скрипт: Уведомить автора Планирования работы ТС")
            Process_1.notify_author(context, None)
            steps_executed.append({
                'step': 'Уведомить автора',
                'type': 'script',
                'result': 'completed'
            })
        else:
            # Ветка "Нет"
            print("  Результат: Нет - создание нового документа")

            # Шаг 2.1: Установить статус Актуально
            print("\n[Шаг 3] Выполняется скрипт: Установить статус Актуально у нового документа")
            Process_1.set_document_active(context, None)
            steps_executed.append({
                'step': 'Установить статус Актуально',
                'type': 'script',
                'result': 'completed'
            })

        # Шаг 3: Создать Планирование работы ТС (пользовательская задача)
        print("\n[Шаг 5] Пользовательская задача: Создать Планирование работы ТС")
        planning_result = {
            'document_id': context.get('new_document_id', 'NEW_DOC_' + str(
                __import__('hashlib').md5(str(__import__('time').time()).encode()).hexdigest()[:8])),
            'author': context.get('author'),
            'calculated_time': context.get('calculated_work_time'),
            'status': context.get('document_status', 'DRAFT'),
            'created_at': str(__import__('datetime').datetime.now())
        }
        context['planning_result'] = planning_result
        steps_executed.append({
            'step': 'Создать Планирование работы ТС',
            'type': 'user_task',
            'result': planning_result
        })

        # Шаг 4: Завершение процесса
        context['status'] = 'COMPLETED'
        context['completed_at'] = str(__import__('datetime').datetime.now())

        print("\n" + "=" * 60)
        print(f"Процесс успешно завершен!")
        print(f"ID документа: {planning_result['document_id']}")
        print(f"Расчетное время: {context.get('calculated_work_time')} м/ч")
        print("=" * 60 + "\n")

        process_instance['steps'] = steps_executed

        return True, "Процесс успешно выполнен", context

    except Exception as e:
        error_msg = f"Ошибка выполнения процесса: {str(e)}"
        print(f"\n[ОШИБКА] {error_msg}")
        context['status'] = 'ERROR'
        context['error'] = error_msg
        return False, error_msg, context


# Функция для получения статуса процесса
def get_process_status(process_instance):
    """Возвращает текущий статус процесса"""
    context = process_instance.get('context', {})
    return {
        'process_id': process_instance.get('process_id'),
        'process_name': process_instance.get('process_name'),
        'status': context.get('status', 'UNKNOWN'),
        'steps_completed': len(process_instance.get('steps', [])),
        'result': context.get('planning_result'),
        'calculated_work_time': context.get('calculated_work_time'),
        'notifications': context.get('notifications', [])
    }