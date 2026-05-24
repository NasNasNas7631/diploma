import time
from datetime import datetime
from process_1 import create_process_instance as create_process_1, execute_process as execute_process_1, \
    get_process_status as get_process_status_1
from process_2 import create_process_instance as create_process_2, execute_process as execute_process_2, \
    get_process_status as get_process_status_2
from process_3 import create_process_instance as create_process_3, execute_process as execute_process_3, \
    get_process_status as get_process_status_3


class ProcessLauncher:
    """
    Класс для запуска процессов Runa WFE.
    Поддерживает process_1, process_2, process_3 и удаленные процессы через REST API
    """

    def __init__(self, base_url=None, username=None, password=None):
        """
        Инициализация. Если передан URL - используем REST API,
        иначе используем локальное выполнение процессов
        """
        self.base_url = base_url
        self.username = username
        self.password = password
        self.use_rest_api = base_url is not None and username is not None
        self.token = None

        # Словарь для хранения запущенных процессов
        self.active_processes = {}
        self.process_counter = 0
        self.process_logs = {}  # Хранилище логов выполнения

        # Маппинг процессов
        self.process_map = {
            'process_1': {
                'create': create_process_1,
                'execute': execute_process_1,
                'get_status': get_process_status_1,
                'name': 'Планирование работы ТС'
            },
            'process_2': {
                'create': create_process_2,
                'execute': execute_process_2,
                'get_status': get_process_status_2,
                'name': 'Планирование ремонтных работ'
            },
            'process_3': {
                'create': create_process_3,
                'execute': execute_process_3,
                'get_status': get_process_status_3,
                'name': 'Производственная программа'
            }
        }

        if self.use_rest_api:
            self._authenticate()

    def _authenticate(self):
        """Аутентификация через REST API Runa WFE"""
        try:
            import requests
            auth_url = f"{self.base_url}/auth/basic"
            response = requests.post(
                auth_url,
                json={"login": self.username, "password": self.password}
            )
            if response.status_code == 200:
                self.token = response.json().get('token')
                self._add_system_log("Аутентификация успешна")
            else:
                self._add_system_log(f"Ошибка аутентификации: {response.status_code}")
        except Exception as e:
            self._add_system_log(f"Ошибка подключения: {e}")

    def _add_system_log(self, message, level="INFO"):
        """Добавить системный лог"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            'type': 'system'
        }
        if 'system_logs' not in self.process_logs:
            self.process_logs['system_logs'] = []
        self.process_logs['system_logs'].append(log_entry)

    def _add_process_log(self, process_id, step, message, level="INFO", step_type="script"):
        """Добавить лог выполнения процесса"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'step': step,
            'message': message,
            'type': step_type
        }
        if process_id not in self.process_logs:
            self.process_logs[process_id] = []
        self.process_logs[process_id].append(log_entry)

    def start_process(self, definition_id, variables=None):
        """
        Запуск процесса по ID определения

        Args:
            definition_id: ID определения процесса (process_1, process_2, process_3 или числовой ID)
            variables: dict с переменными процесса
        """
        if variables is None:
            variables = {}

        self._add_system_log(f"Запуск процесса {definition_id} с переменными: {variables}")

        # Проверяем локальные процессы
        if definition_id in self.process_map:
            return self._start_local_process(definition_id, variables)
        elif definition_id == 1 or definition_id == '1':
            return self._start_local_process('process_1', variables)
        elif definition_id == 2 or definition_id == '2':
            return self._start_local_process('process_2', variables)
        elif definition_id == 3 or definition_id == '3':
            return self._start_local_process('process_3', variables)
        elif self.use_rest_api:
            return self._start_remote_process(definition_id, variables)
        else:
            raise Exception(
                f"Неизвестный процесс: {definition_id}. Доступные процессы: {list(self.process_map.keys())}")

    def _start_local_process(self, process_key, variables):
        """Локальный запуск процесса с детальным логированием"""
        self.process_counter += 1
        process_instance_id = f"{process_key}_{self.process_counter}_{int(time.time())}"

        process_info = self.process_map[process_key]

        self._add_process_log(process_instance_id, "init", f"Создание экземпляра процесса {process_info['name']}",
                              "INFO", "system")

        # Создаем экземпляр процесса
        process_instance = process_info['create'](variables)
        self._add_process_log(process_instance_id, "init", f"Процесс создан с переменными: {variables}", "INFO",
                              "system")

        # Выполняем процесс с логированием в зависимости от типа
        if process_key == 'process_1':
            success, message, final_context = self._execute_process_1_with_logging(process_instance_id,
                                                                                   process_instance)
        elif process_key == 'process_2':
            success, message, final_context = self._execute_process_2_with_logging(process_instance_id,
                                                                                   process_instance)
        elif process_key == 'process_3':
            success, message, final_context = self._execute_process_3_with_logging(process_instance_id,
                                                                                   process_instance)
        else:
            success, message, final_context = process_info['execute'](process_instance)

        if success:
            # Сохраняем информацию о процессе
            self.active_processes[process_instance_id] = {
                'process_key': process_key,
                'process_name': process_info['name'],
                'instance': process_instance,
                'context': final_context,
                'status': 'COMPLETED',
                'started_at': datetime.now().isoformat()
            }

            self._add_process_log(process_instance_id, "complete", f"Процесс успешно завершен: {message}", "INFO",
                                  "system")

            return {
                'process_instance_id': process_instance_id,
                'process_key': process_key,
                'status': 'success',
                'message': message,
                'result': self._extract_process_result(process_key, final_context)
            }
        else:
            self._add_process_log(process_instance_id, "error", f"Ошибка выполнения: {message}", "ERROR", "system")
            raise Exception(f"Ошибка запуска {process_key}: {message}")

    def _execute_process_1_with_logging(self, process_id, process_instance):
        """Выполнение process_1 с детальным логированием"""
        context = process_instance['context']
        steps_executed = []

        try:
            from process_1 import Process_1

            self._add_process_log(process_id, "start", f"Запуск процесса: {process_instance['process_name']}", "INFO",
                                  "system")

            # Шаг 1: Авторасчет Время работы м/ч
            self._add_process_log(process_id, "Авторасчет", "Начало расчета времени работы", "INFO", "script")
            Process_1.calculate_work_time(context, None)
            self._add_process_log(process_id, "Авторасчет",
                                  f"Расчет завершен. Время работы: {context.get('calculated_work_time')} м/ч", "INFO",
                                  "script")
            steps_executed.append({
                'step': 'Авторасчет Время работы м/ч',
                'type': 'script',
                'result': 'completed'
            })

            # Шаг 2: Проверка условия
            self._add_process_log(process_id, "Проверка условия", "Анализ необходимости обновления документа", "INFO",
                                  "decision")
            need_update = Process_1.check_need_update(context, None)

            if need_update:
                self._add_process_log(process_id, "Проверка условия", "Решение: ДА - требуется обновление", "INFO",
                                      "decision")

                # Шаг 2.1: Установить статус Неактуально
                self._add_process_log(process_id, "Обновление статуса",
                                      "Установка статуса 'Неактуально' для старого документа", "INFO", "script")
                Process_1.is_document_outdated(context, None)
                self._add_process_log(process_id, "Обновление статуса", "Статус старого документа обновлен", "INFO",
                                      "script")
                steps_executed.append({
                    'step': 'Установить статус Неактуально',
                    'type': 'script',
                    'result': 'completed'
                })

                # Шаг 2.2: Уведомить автора
                self._add_process_log(process_id, "Уведомление", "Отправка уведомления автору", "INFO", "script")
                Process_1.notify_author(context, None)
                self._add_process_log(process_id, "Уведомление",
                                      f"Уведомление отправлено автору {context.get('author')}", "INFO", "script")
                steps_executed.append({
                    'step': 'Уведомить автора',
                    'type': 'script',
                    'result': 'completed'
                })
            else:
                self._add_process_log(process_id, "Проверка условия", "Решение: НЕТ - создание нового документа",
                                      "INFO", "decision")

                # Шаг 2.1: Установить статус Актуально
                self._add_process_log(process_id, "Создание документа",
                                      "Установка статуса 'Актуально' для нового документа", "INFO", "script")
                Process_1.set_document_active(context, None)
                self._add_process_log(process_id, "Создание документа", "Статус нового документа установлен", "INFO",
                                      "script")
                steps_executed.append({
                    'step': 'Установить статус Актуально',
                    'type': 'script',
                    'result': 'completed'
                })

            # Шаг 3: Создать Планирование работы ТС
            self._add_process_log(process_id, "Планирование", "Создание планирования работы ТС", "INFO", "user_task")
            planning_result = {
                'document_id': context.get('new_document_id', 'NEW_DOC_' + str(
                    __import__('hashlib').md5(str(time.time()).encode()).hexdigest()[:8])),
                'author': context.get('author'),
                'calculated_time': context.get('calculated_work_time'),
                'status': context.get('document_status', 'DRAFT'),
                'created_at': datetime.now().isoformat()
            }
            context['planning_result'] = planning_result
            self._add_process_log(process_id, "Планирование", f"Планирование создано: {planning_result}", "INFO",
                                  "user_task")
            steps_executed.append({
                'step': 'Создать Планирование работы ТС',
                'type': 'user_task',
                'result': planning_result
            })

            # Завершение
            context['status'] = 'COMPLETED'
            context['completed_at'] = datetime.now().isoformat()
            process_instance['steps'] = steps_executed

            return True, "Процесс успешно выполнен", context

        except Exception as e:
            error_msg = f"Ошибка выполнения процесса: {str(e)}"
            self._add_process_log(process_id, "error", error_msg, "ERROR", "system")
            context['status'] = 'ERROR'
            context['error'] = error_msg
            return False, error_msg, context

    def _execute_process_2_with_logging(self, process_id, process_instance):
        """Выполнение process_2 с детальным логированием"""
        context = process_instance['context']
        steps_executed = []

        try:
            from process_2 import Process_2

            self._add_process_log(process_id, "start", f"Запуск процесса: {process_instance['process_name']}", "INFO",
                                  "system")
            self._add_process_log(process_id, "init", f"Документ: {context.get('document_id')}", "INFO", "system")
            self._add_process_log(process_id, "init",
                                  f"Оборудование: {context.get('equipment_type')} (ID: {context.get('equipment_id')})",
                                  "INFO", "system")

            # Шаг 1: Планировать ремонтные работы
            self._add_process_log(process_id, "Планирование ремонта", "Инициализация планирования ремонтных работ",
                                  "INFO", "script")
            self._add_process_log(process_id, "Планирование ремонта", f"  - Тип ТС: {context.get('equipment_type')}",
                                  "INFO", "script")
            self._add_process_log(process_id, "Планирование ремонта",
                                  f"  - Возраст: {context.get('equipment_age')} лет", "INFO", "script")
            self._add_process_log(process_id, "Планирование ремонта",
                                  f"  - Часы работы: {context.get('total_operating_hours')} ч", "INFO", "script")
            self._add_process_log(process_id, "Планирование ремонта",
                                  f"  - Серьезность: {context.get('breakdown_severity')}", "INFO", "script")
            steps_executed.append({
                'step': 'Планировать ремонтные работы',
                'type': 'script',
                'result': 'initialized'
            })

            # Шаг 2: Проверка условия
            self._add_process_log(process_id, "Проверка условия", "Анализ необходимости капитального ремонта", "INFO",
                                  "decision")
            need_major_repair = Process_2.should_do_major_repair(context)

            if need_major_repair:
                self._add_process_log(process_id, "Проверка условия", "Решение: ДА - требуется детальная диагностика",
                                      "INFO", "decision")

                # Шаг 2.1: Установить флаг ремонта
                self._add_process_log(process_id, "Установка флага",
                                      "Установка флага Восстановительный/Капитальный ремонт", "INFO", "script")
                Process_2.set_repair_flag(context, None)
                self._add_process_log(process_id, "Установка флага", f"Тип ремонта: {context.get('repair_type')}",
                                      "INFO", "script")
                self._add_process_log(process_id, "Установка флага", f"Причина: {context.get('repair_reason')}", "INFO",
                                      "script")
                steps_executed.append({
                    'step': 'Установить флаг ремонта',
                    'type': 'script',
                    'result': 'completed',
                    'data': {'repair_type': context.get('repair_type')}
                })

                # Шаг 2.2: Проверить VIN и группу
                self._add_process_log(process_id, "Проверка VIN", "Проверка VIN и группы Сторонние", "INFO", "script")
                Process_2.check_vin_and_group(context, None)
                self._add_process_log(process_id, "Проверка VIN", f"Результат: {context.get('vin_check_message')}",
                                      "INFO", "script")
                self._add_process_log(process_id, "Проверка VIN",
                                      f"Стороннее оборудование: {context.get('is_third_party')}", "INFO", "script")
                steps_executed.append({
                    'step': 'Проверить VIN и группу',
                    'type': 'script',
                    'result': 'completed',
                    'data': {
                        'vin_valid': context.get('vin_valid'),
                        'is_third_party': context.get('is_third_party')
                    }
                })
            else:
                self._add_process_log(process_id, "Проверка условия", "Решение: НЕТ - стандартная процедура", "INFO",
                                      "decision")

                # Шаг 2.1: Проверить VIN и группу
                self._add_process_log(process_id, "Проверка VIN", "Проверка VIN и группы Сторонние", "INFO", "script")
                Process_2.check_vin_and_group(context, None)
                self._add_process_log(process_id, "Проверка VIN", f"Результат: {context.get('vin_check_message')}",
                                      "INFO", "script")
                self._add_process_log(process_id, "Проверка VIN",
                                      f"Стороннее оборудование: {context.get('is_third_party')}", "INFO", "script")
                steps_executed.append({
                    'step': 'Проверить VIN и группу',
                    'type': 'script',
                    'result': 'completed',
                    'data': {
                        'vin_valid': context.get('vin_valid'),
                        'is_third_party': context.get('is_third_party')
                    }
                })

            # Шаг 3: Ввести стоимость
            self._add_process_log(process_id, "Ввод стоимости", "Ввод стоимости (Ремонт/Закупка)", "INFO", "user_task")

            cost_estimate = Process_2.calculate_costs(context)
            repair_cost = context.get('repair_cost', cost_estimate['repair_cost'])
            procurement_cost = context.get('procurement_cost', cost_estimate['procurement_cost'])
            total_cost = repair_cost + procurement_cost

            context['repair_cost'] = repair_cost
            context['procurement_cost'] = procurement_cost
            context['total_cost'] = total_cost

            self._add_process_log(process_id, "Ввод стоимости", f"Стоимость ремонта: {repair_cost:,.2f} руб.", "INFO",
                                  "user_task")
            self._add_process_log(process_id, "Ввод стоимости", f"Стоимость закупки: {procurement_cost:,.2f} руб.",
                                  "INFO", "user_task")
            self._add_process_log(process_id, "Ввод стоимости", f"Общая стоимость: {total_cost:,.2f} руб.", "INFO",
                                  "user_task")
            steps_executed.append({
                'step': 'Ввести стоимость',
                'type': 'user_task',
                'result': {
                    'repair_cost': repair_cost,
                    'procurement_cost': procurement_cost,
                    'total_cost': total_cost
                }
            })

            # Шаг 4: Провести документ
            self._add_process_log(process_id, "Проведение документа", "Проведение документа", "INFO", "user_task")
            context['document_approved'] = True
            context['document_approved_at'] = datetime.now().isoformat()
            self._add_process_log(process_id, "Проведение документа", f"Документ {context.get('document_id')} проведен",
                                  "SUCCESS", "user_task")
            steps_executed.append({
                'step': 'Провести документ',
                'type': 'user_task',
                'result': {'document_id': context.get('document_id'), 'approved': True}
            })

            # Шаг 5: Записать в регистр
            self._add_process_log(process_id, "Запись в регистр", "Запись движений в регистр Показатели планированияТС",
                                  "INFO", "script")
            Process_2.write_to_planning_register(context, None)
            self._add_process_log(process_id, "Запись в регистр", "Показатели успешно записаны в регистр", "SUCCESS",
                                  "script")
            steps_executed.append({
                'step': 'Записать в регистр',
                'type': 'script',
                'result': 'completed'
            })

            # Шаг 6: Создать ABC-анализ
            self._add_process_log(process_id, "ABC-анализ", "Создание ABC-анализа", "INFO", "user_task")

            total_cost = context.get('total_cost', 0)
            repair_type = context.get('repair_type', 'Текущий ремонт')

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
            self._add_process_log(process_id, "ABC-анализ", f"Результат ABC-анализа: Класс {abc_class}", "SUCCESS",
                                  "user_task")
            self._add_process_log(process_id, "ABC-анализ", f"Рекомендация: {abc_recommendation}", "INFO", "user_task")
            steps_executed.append({
                'step': 'Создать ABC-анализ',
                'type': 'user_task',
                'result': abc_analysis
            })

            # Завершение
            context['status'] = 'COMPLETED'
            context['completed_at'] = datetime.now().isoformat()
            process_instance['steps'] = steps_executed

            self._add_process_log(process_id, "complete",
                                  f"Процесс успешно завершен! Общая стоимость: {total_cost:,.2f} руб.", "SUCCESS",
                                  "system")

            return True, "Процесс успешно выполнен", context

        except Exception as e:
            error_msg = f"Ошибка выполнения процесса: {str(e)}"
            self._add_process_log(process_id, "error", error_msg, "ERROR", "system")
            context['status'] = 'ERROR'
            context['error'] = error_msg
            return False, error_msg, context

    def _execute_process_3_with_logging(self, process_id, process_instance):
        """Выполнение process_3 с детальным логированием"""
        context = process_instance['context']
        steps_executed = []

        try:
            from process_3 import Process_3

            self._add_process_log(process_id, "start", f"Запуск процесса: {process_instance['process_name']}", "INFO",
                                  "system")
            self._add_process_log(process_id, "init", f"Период: {context.get('production_period')}", "INFO", "system")
            self._add_process_log(process_id, "init", f"Документ: {context.get('new_document_id')}", "INFO", "system")

            # Шаг 1: Создать производственную программу (инициализация)
            self._add_process_log(process_id, "Инициализация", "Создание производственной программы", "INFO", "system")
            steps_executed.append({
                'step': 'Создать производственную программу',
                'type': 'script',
                'result': 'initialized'
            })

            # Шаг 2: Автозаполнение ТЧ
            self._add_process_log(process_id, "Автозаполнение", "Автозаполнение ТЧ из Закрепления ТС и Потребности ТС",
                                  "INFO", "script")
            Process_3.auto_fill_from_assignments(context, None)
            self._add_process_log(process_id, "Автозаполнение",
                                  f"Заполнено {context.get('total_equipment_count', 0)} позиций", "INFO", "script")
            self._add_process_log(process_id, "Автозаполнение",
                                  f"Всего плановых часов: {context.get('total_planned_hours', 0):.2f}", "INFO",
                                  "script")
            steps_executed.append({
                'step': 'Автозаполнение ТЧ',
                'type': 'script',
                'result': 'completed'
            })

            # Шаг 3: Пересчет км
            self._add_process_log(process_id, "Пересчет км", "Пересчет км для автотранспорта", "INFO", "script")
            Process_3.recalculate_mileage(context, None)
            self._add_process_log(process_id, "Пересчет км",
                                  f"Общий километраж: {context.get('total_mileage', 0):.2f} км", "INFO", "script")
            self._add_process_log(process_id, "Пересчет км",
                                  f"Общие затраты: {context.get('total_transport_cost', 0):,.2f} руб.", "INFO",
                                  "script")
            steps_executed.append({
                'step': 'Пересчет км',
                'type': 'script',
                'result': 'completed'
            })

            # Шаг 4: Первый эксклюзивный шлюз
            self._add_process_log(process_id, "Проверка обновления", "Анализ необходимости обновления документа",
                                  "INFO", "decision")
            need_update = Process_3.should_update_old_document(context)

            if need_update:
                self._add_process_log(process_id, "Проверка обновления",
                                      "Решение: ДА - требуется обновление старого документа", "INFO", "decision")

                # Установить статус Неактуально
                self._add_process_log(process_id, "Обновление статуса",
                                      "Установка статуса 'Неактуально' у старого документа", "INFO", "script")
                Process_3.set_old_document_inactive(context, None)
                self._add_process_log(process_id, "Обновление статуса", "Старый документ помечен как Неактуально",
                                      "SUCCESS", "script")
                steps_executed.append({
                    'step': 'Установить статус Неактуально',
                    'type': 'script',
                    'result': 'completed'
                })
            else:
                self._add_process_log(process_id, "Проверка обновления", "Решение: НЕТ - создание нового документа",
                                      "INFO", "decision")

                # Установить статус Актуально
                self._add_process_log(process_id, "Создание документа",
                                      "Установка статуса 'Актуально' у нового документа", "INFO", "script")
                Process_3.set_new_document_active(context, None)
                self._add_process_log(process_id, "Создание документа",
                                      f"Новый документ {context.get('new_document_id')} (версия {context.get('document_version', 1)}) создан",
                                      "SUCCESS", "script")
                steps_executed.append({
                    'step': 'Установить статус Актуально',
                    'type': 'script',
                    'result': 'completed'
                })

            # Шаг 5: Создать производственную программу (пользовательская задача)
            self._add_process_log(process_id, "Создание программы", "Создание производственной программы", "INFO",
                                  "user_task")
            production_program = {
                'document_id': context.get('new_document_id'),
                'period': context.get('production_period'),
                'total_hours': context.get('total_planned_hours'),
                'total_cost': context.get('total_transport_cost'),
                'status': context.get('document_status', 'Черновик')
            }
            self._add_process_log(process_id, "Создание программы",
                                  f"Производственная программа создана: {production_program['document_id']}", "SUCCESS",
                                  "user_task")
            steps_executed.append({
                'step': 'Создать производственную программу',
                'type': 'user_task',
                'result': production_program
            })

            # Шаг 6: Согласовать документ
            self._add_process_log(process_id, "Согласование", "Согласование документа", "INFO", "user_task")

            if context.get('approval_status') == 'draft':
                context['approval_status'] = 'approved'

            self._add_process_log(process_id, "Согласование", f"Статус согласования: {context.get('approval_status')}",
                                  "INFO", "user_task")
            if context.get('approval_comments'):
                self._add_process_log(process_id, "Согласование", f"Замечания: {context.get('approval_comments')}",
                                      "WARNING", "user_task")
            steps_executed.append({
                'step': 'Согласовать документ',
                'type': 'user_task',
                'result': {'status': context.get('approval_status')}
            })

            # Шаг 7: Второй эксклюзивный шлюз
            self._add_process_log(process_id, "Проверка согласования", "Проверка результата согласования", "INFO",
                                  "decision")
            is_approved = Process_3.is_approved(context)

            if is_approved:
                self._add_process_log(process_id, "Проверка согласования", "Решение: ДА - документ согласован",
                                      "SUCCESS", "decision")

                # Подписать документ
                self._add_process_log(process_id, "Подписание", "Подписание документа", "INFO", "user_task")
                context['signed_by'] = context.get('signed_by', context.get('created_by'))
                context['signed_at'] = datetime.now().isoformat()
                context['approval_status'] = 'signed'
                self._add_process_log(process_id, "Подписание", f"Документ подписан: {context['signed_by']}", "SUCCESS",
                                      "user_task")
                steps_executed.append({
                    'step': 'Подписать документ',
                    'type': 'user_task',
                    'result': {'signed_by': context['signed_by']}
                })

                # Записать в регистр
                self._add_process_log(process_id, "Запись в регистр",
                                      "Запись движений в регистр Обороты производственной программы", "INFO", "script")
                Process_3.write_to_production_register(context, None)
                self._add_process_log(process_id, "Запись в регистр", "Производственная программа записана в регистр",
                                      "SUCCESS", "script")
                steps_executed.append({
                    'step': 'Записать в регистр',
                    'type': 'script',
                    'result': 'completed'
                })

                # Создать печатные формы
                self._add_process_log(process_id, "Печатные формы", "Создание печатных форм", "INFO", "user_task")
                printed_forms = [
                    {'type': 'План-график', 'filename': f"{context.get('new_document_id')}_План-график.pdf"},
                    {'type': 'Смета затрат', 'filename': f"{context.get('new_document_id')}_Смета затрат.pdf"},
                    {'type': 'Потребность в ТС', 'filename': f"{context.get('new_document_id')}_Потребность в ТС.pdf"},
                    {'type': 'Расчет ГСМ', 'filename': f"{context.get('new_document_id')}_Расчет ГСМ.pdf"}
                ]
                context['printed_forms'] = printed_forms
                self._add_process_log(process_id, "Печатные формы", f"Создано {len(printed_forms)} печатных форм",
                                      "SUCCESS", "user_task")
                steps_executed.append({
                    'step': 'Создать печатные формы',
                    'type': 'user_task',
                    'result': {'forms_count': len(printed_forms)}
                })
            else:
                self._add_process_log(process_id, "Проверка согласования", "Решение: НЕТ - требуется доработка",
                                      "WARNING", "decision")
                self._add_process_log(process_id, "Доработка", "Документ отправлен на доработку", "WARNING", "system")
                context['approval_status'] = 'rejected'
                context['need_rework'] = True
                context['rework_count'] = context.get('rework_count', 0) + 1
                steps_executed.append({
                    'step': 'Доработка документа',
                    'type': 'decision',
                    'result': 'return_to_auto_fill'
                })

                context['status'] = 'REWORK_NEEDED'
                context['completed_at'] = datetime.now().isoformat()
                process_instance['steps'] = steps_executed

                return False, "Документ требует доработки. Пожалуйста, исправьте замечания и запустите процесс заново.", context

            # Завершение
            context['status'] = 'COMPLETED'
            context['completed_at'] = datetime.now().isoformat()
            process_instance['steps'] = steps_executed

            self._add_process_log(process_id, "complete",
                                  f"Процесс успешно завершен! Создано {len(printed_forms)} печатных форм", "SUCCESS",
                                  "system")

            return True, "Процесс успешно выполнен", context

        except Exception as e:
            error_msg = f"Ошибка выполнения процесса: {str(e)}"
            self._add_process_log(process_id, "error", error_msg, "ERROR", "system")
            context['status'] = 'ERROR'
            context['error'] = error_msg
            return False, error_msg, context

    def _extract_process_result(self, process_key, context):
        """Извлекает релевантный результат из контекста процесса"""
        if process_key == 'process_1':
            return context.get('planning_result')
        elif process_key == 'process_2':
            return {
                'document_id': context.get('document_id'),
                'repair_type': context.get('repair_type'),
                'total_cost': context.get('total_cost'),
                'abc_analysis': context.get('abc_analysis_result'),
                'is_third_party': context.get('is_third_party'),
                'planning_records': len(context.get('planning_register', []))
            }
        elif process_key == 'process_3':
            return {
                'document_id': context.get('new_document_id'),
                'document_version': context.get('document_version', 1),
                'production_period': context.get('production_period'),
                'total_planned_hours': context.get('total_planned_hours'),
                'total_equipment_count': context.get('total_equipment_count'),
                'total_mileage': context.get('total_mileage'),
                'total_transport_cost': context.get('total_transport_cost'),
                'approval_status': context.get('approval_status'),
                'printed_forms': context.get('printed_forms', []),
                'rework_count': context.get('rework_count', 0)
            }
        return None

    def _start_remote_process(self, definition_id, variables):
        """Запуск процесса через REST API Runa WFE"""
        if not self.token:
            self._authenticate()

        try:
            import requests
            headers = {"Authorization": f"Bearer {self.token}"}
            payload = {
                "definitionId": definition_id,
                "variables": variables
            }

            response = requests.post(
                f"{self.base_url}/process/start",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()

            return {
                'process_instance_id': result.get('processInstanceId'),
                'status': 'success'
            }
        except Exception as e:
            raise Exception(f"Ошибка запуска удаленного процесса: {e}")

    def get_process_status(self, process_instance_id):
        """Получить статус процесса по ID"""
        if process_instance_id in self.active_processes:
            process_data = self.active_processes[process_instance_id]
            process_key = process_data['process_key']
            get_status_func = self.process_map[process_key]['get_status']
            return get_status_func(process_data['instance'])
        elif self.use_rest_api:
            return {'status': 'UNKNOWN', 'message': 'Статус недоступен'}
        else:
            return None

    def get_process_logs(self, process_instance_id):
        """Получить логи выполнения процесса"""
        return self.process_logs.get(process_instance_id, [])

    def get_process_steps(self, process_instance_id):
        """Получить шаги выполнения процесса"""
        if process_instance_id in self.active_processes:
            process_data = self.active_processes[process_instance_id]
            return process_data['instance'].get('steps', [])
        return []

    def get_process_result(self, process_instance_id):
        """Получить результат выполнения процесса"""
        if process_instance_id in self.active_processes:
            process_data = self.active_processes[process_instance_id]
            return self._extract_process_result(
                process_data['process_key'],
                process_data['context']
            )
        return None

    def list_active_processes(self):
        """Список активных процессов"""
        return list(self.active_processes.keys())

    def get_available_processes(self):
        """Список доступных процессов"""
        return [
            {'key': key, 'name': info['name']}
            for key, info in self.process_map.items()
        ]