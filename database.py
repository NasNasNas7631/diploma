import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2.pool import SimpleConnectionPool
from datetime import datetime
import json
import os
from typing import Dict, Any, List, Optional


class Database:
    """Класс для работы с PostgreSQL"""

    def __init__(self):
        self.pool = None
        self.init_pool()
        self.init_tables()

    def init_pool(self):
        """Инициализация пула соединений"""
        self.pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host='localhost',
            port='5432',
            database='runa_wfe',
            user='postgres',
            password='postgre'
        )

    def get_connection(self):
        """Получить соединение из пула"""
        return self.pool.getconn()

    def return_connection(self, conn):
        """Вернуть соединение в пул"""
        self.pool.putconn(conn)

    def init_tables(self):
        """Создание таблиц, если они не существуют"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            # Таблица определений процессов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS procDef (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    version INTEGER DEFAULT 1,
                    is_active BOOLEAN DEFAULT TRUE,
                    bpmn_diagram VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица переменных процессов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS procVar (
                    id SERIAL PRIMARY KEY,
                    proc_id VARCHAR(50) REFERENCES procDef(id) ON DELETE CASCADE,
                    var_name VARCHAR(100) NOT NULL,
                    var_type VARCHAR(50) NOT NULL,
                    description TEXT,
                    is_required BOOLEAN DEFAULT FALSE,
                    default_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(proc_id, var_name)
                )
            """)

            # Таблица истории выполнения
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS procHist (
                    id SERIAL PRIMARY KEY,
                    instance_id VARCHAR(100) UNIQUE NOT NULL,
                    proc_id VARCHAR(50) REFERENCES procDef(id),
                    proc_name VARCHAR(200),
                    status VARCHAR(50) DEFAULT 'IN_PROGRESS',
                    variables JSONB,
                    steps JSONB,
                    logs JSONB,
                    result JSONB,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    duration_seconds FLOAT,
                    created_by VARCHAR(100),
                    error_message TEXT
                )
            """)

            # Индексы для оптимизации
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_proc_hist_proc_id ON procHist(proc_id);
                CREATE INDEX IF NOT EXISTS idx_proc_hist_status ON procHist(status);
                CREATE INDEX IF NOT EXISTS idx_proc_hist_started_at ON procHist(started_at);
                CREATE INDEX IF NOT EXISTS idx_proc_hist_instance_id ON procHist(instance_id);
            """)

            # Триггер для обновления updated_at
            cursor.execute("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """)

            cursor.execute("""
                DROP TRIGGER IF EXISTS update_procDef_updated_at ON procDef;
                CREATE TRIGGER update_procDef_updated_at
                    BEFORE UPDATE ON procDef
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
            """)

            conn.commit()
            print("Таблицы успешно созданы/проверены")

            # Инициализация процессов по умолчанию
            self.init_default_processes()

        except Exception as e:
            print(f"Ошибка при создании таблиц: {e}")
            conn.rollback()
        finally:
            cursor.close()
            self.return_connection(conn)

    def init_default_processes(self):
        """Инициализация процессов по умолчанию"""
        processes = [
            {
                'id': 'process_1',
                'name': 'Планирование работы ТС',
                'description': 'Процесс планирования работы транспортных средств с автоматическим расчетом времени',
                'variables': [
                    {'name': 'equipment_type', 'type': 'string', 'required': True,
                     'description': 'Тип транспортного средства'},
                    {'name': 'work_volume', 'type': 'number', 'required': True, 'description': 'Объем работ'},
                    {'name': 'author', 'type': 'string', 'required': True, 'description': 'Автор документа'},
                    {'name': 'planned_hours', 'type': 'number', 'required': False, 'description': 'Плановые часы',
                     'default': '0'},
                    {'name': 'old_document_id', 'type': 'string', 'required': False,
                     'description': 'ID старого документа'},
                    {'name': 'new_document_id', 'type': 'string', 'required': False,
                     'description': 'ID нового документа'},
                    {'name': 'force_update', 'type': 'boolean', 'required': False,
                     'description': 'Принудительное обновление', 'default': 'false'}
                ]
            },
            {
                'id': 'process_2',
                'name': 'Планирование ремонтных работ',
                'description': 'Процесс планирования ремонтных работ с ABC-анализом',
                'variables': [
                    {'name': 'equipment_type', 'type': 'string', 'required': True, 'description': 'Тип оборудования'},
                    {'name': 'equipment_id', 'type': 'string', 'required': True, 'description': 'ID оборудования'},
                    {'name': 'equipment_age', 'type': 'number', 'required': True,
                     'description': 'Возраст оборудования'},
                    {'name': 'total_operating_hours', 'type': 'number', 'required': True,
                     'description': 'Общее время работы'},
                    {'name': 'breakdown_severity', 'type': 'string', 'required': True,
                     'description': 'Серьезность поломки'},
                    {'name': 'created_by', 'type': 'string', 'required': True, 'description': 'Создатель'},
                    {'name': 'vin_code', 'type': 'string', 'required': False, 'description': 'VIN код'},
                    {'name': 'document_id', 'type': 'string', 'required': False, 'description': 'ID документа'}
                ]
            },
            {
                'id': 'process_3',
                'name': 'Производственная программа',
                'description': 'Процесс создания производственной программы с согласованием',
                'variables': [
                    {'name': 'production_period', 'type': 'string', 'required': True,
                     'description': 'Период производства'},
                    {'name': 'created_by', 'type': 'string', 'required': True, 'description': 'Создатель'},
                    {'name': 'old_document_id', 'type': 'string', 'required': False,
                     'description': 'ID старого документа'},
                    {'name': 'new_document_id', 'type': 'string', 'required': False,
                     'description': 'ID нового документа'},
                    {'name': 'force_update', 'type': 'boolean', 'required': False,
                     'description': 'Принудительное обновление', 'default': 'false'}
                ]
            }
        ]

        for proc in processes:
            if not self.get_process_definition(proc['id']):
                self.add_process_definition(proc['id'], proc['name'], proc['description'], proc['variables'])

    def add_process_definition(self, proc_id: str, name: str, description: str, variables: List[Dict]):
        """Добавление определения процесса"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            # Добавляем процесс
            cursor.execute("""
                INSERT INTO procDef (id, name, description, version, is_active)
                VALUES (%s, %s, %s, 1, TRUE)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    is_active = TRUE
            """, (proc_id, name, description))

            # Добавляем переменные
            for var in variables:
                cursor.execute("""
                    INSERT INTO procVar (proc_id, var_name, var_type, description, is_required, default_value)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (proc_id, var_name) DO UPDATE SET
                        var_type = EXCLUDED.var_type,
                        description = EXCLUDED.description,
                        is_required = EXCLUDED.is_required,
                        default_value = EXCLUDED.default_value
                """, (proc_id, var['name'], var['type'], var.get('description', ''),
                      var.get('required', False), var.get('default', None)))

            conn.commit()
            print(f"Процесс {proc_id} добавлен/обновлен")
        except Exception as e:
            print(f"Ошибка при добавлении процесса {proc_id}: {e}")
            conn.rollback()
        finally:
            cursor.close()
            self.return_connection(conn)

    def get_process_definition(self, proc_id: str) -> Optional[Dict]:
        """Получение определения процесса"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT * FROM procDef WHERE id = %s AND is_active = TRUE
            """, (proc_id,))
            process = cursor.fetchone()

            if process:
                cursor.execute("""
                    SELECT var_name, var_type, description, is_required, default_value
                    FROM procVar
                    WHERE proc_id = %s
                    ORDER BY id
                """, (proc_id,))
                variables = cursor.fetchall()
                process['variables'] = variables

            return process
        except Exception as e:
            print(f"Ошибка при получении процесса {proc_id}: {e}")
            return None
        finally:
            cursor.close()
            self.return_connection(conn)

    def get_all_process_definitions(self) -> List[Dict]:
        """Получение всех определений процессов"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT * FROM procDef WHERE is_active = TRUE ORDER BY id
            """)
            processes = cursor.fetchall()

            for process in processes:
                cursor.execute("""
                    SELECT var_name, var_type, description, is_required, default_value
                    FROM procVar
                    WHERE proc_id = %s
                    ORDER BY id
                """, (process['id'],))
                process['variables'] = cursor.fetchall()

            return processes
        except Exception as e:
            print(f"Ошибка при получении процессов: {e}")
            return []
        finally:
            cursor.close()
            self.return_connection(conn)

    def save_process_history(self, instance_id: str, proc_id: str, proc_name: str,
                             variables: Dict, steps: List, logs: List,
                             result: Dict, status: str, error: str = None,
                             created_by: str = 'system'):
        """Сохранение истории выполнения процесса"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            # Проверяем, существует ли уже запись
            cursor.execute("SELECT started_at FROM procHist WHERE instance_id = %s", (instance_id,))
            existing = cursor.fetchone()

            completed_at = datetime.now() if status in ['COMPLETED', 'ERROR', 'REWORK_NEEDED'] else None
            duration = None

            if existing and existing[0] and completed_at:
                duration = (completed_at - existing[0]).total_seconds()

            # Используем Json для автоматической сериализации
            cursor.execute("""
                INSERT INTO procHist (
                    instance_id, proc_id, proc_name, status, 
                    variables, steps, logs, result,
                    completed_at, duration_seconds, created_by, error_message
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (instance_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    steps = EXCLUDED.steps,
                    logs = EXCLUDED.logs,
                    result = EXCLUDED.result,
                    completed_at = EXCLUDED.completed_at,
                    duration_seconds = EXCLUDED.duration_seconds,
                    error_message = EXCLUDED.error_message
            """, (
                instance_id, proc_id, proc_name, status,
                Json(variables) if variables else None,
                Json(steps) if steps else None,
                Json(logs) if logs else None,
                Json(result) if result else None,
                completed_at, duration, created_by, error
            ))

            conn.commit()
            print(f"История сохранена для процесса {instance_id}")
        except Exception as e:
            print(f"Ошибка при сохранении истории: {e}")
            conn.rollback()
        finally:
            cursor.close()
            self.return_connection(conn)

    def get_process_history(self, instance_id: str = None, proc_id: str = None,
                            limit: int = 100, offset: int = 0) -> List[Dict]:
        """Получение истории выполнения процессов"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            query = """
                SELECT 
                    id, instance_id, proc_id, proc_name, status,
                    variables, steps, logs, result,
                    started_at, completed_at, duration_seconds, 
                    created_by, error_message
                FROM procHist 
                WHERE 1=1
            """
            params = []

            if instance_id:
                query += " AND instance_id = %s"
                params.append(instance_id)
            if proc_id:
                query += " AND proc_id = %s"
                params.append(proc_id)

            query += " ORDER BY started_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cursor.execute(query, params)
            records = cursor.fetchall()

            # Преобразуем данные
            for record in records:
                # Конвертируем datetime в строку для JSON
                if record.get('started_at') and isinstance(record['started_at'], datetime):
                    record['started_at'] = record['started_at'].isoformat()
                if record.get('completed_at') and isinstance(record['completed_at'], datetime):
                    record['completed_at'] = record['completed_at'].isoformat()

                # Парсим JSON поля
                for field in ['variables', 'steps', 'logs', 'result']:
                    value = record.get(field)
                    if value is None:
                        record[field] = {} if field in ['variables', 'result'] else []
                    elif isinstance(value, str):
                        try:
                            record[field] = json.loads(value)
                        except:
                            record[field] = {} if field in ['variables', 'result'] else []
                    elif isinstance(value, (dict, list)):
                        pass  # Уже правильный формат
                    else:
                        record[field] = {} if field in ['variables', 'result'] else []

            return records
        except Exception as e:
            print(f"Ошибка при получении истории: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            cursor.close()
            self.return_connection(conn)

    def get_process_statistics(self) -> Dict:
        """Получение статистики по процессам"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Общая статистика
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_runs,
                    COUNT(DISTINCT proc_id) as unique_processes,
                    SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END) as failed,
                    AVG(duration_seconds) as avg_duration
                FROM procHist
            """)
            stats = cursor.fetchone()

            # Статистика по процессам
            cursor.execute("""
                SELECT 
                    proc_id,
                    proc_name,
                    COUNT(*) as runs,
                    SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as successful,
                    AVG(duration_seconds) as avg_duration
                FROM procHist
                GROUP BY proc_id, proc_name
                ORDER BY runs DESC
            """)
            by_process = cursor.fetchall()

            return {
                'total_runs': stats['total_runs'] or 0,
                'unique_processes': stats['unique_processes'] or 0,
                'successful': stats['successful'] or 0,
                'failed': stats['failed'] or 0,
                'avg_duration': round(stats['avg_duration'] or 0, 2),
                'by_process': by_process
            }
        except Exception as e:
            print(f"Ошибка при получении статистики: {e}")
            return {}
        finally:
            cursor.close()
            self.return_connection(conn)

    def delete_process_history(self, instance_id: str = None, days_old: int = None):
        """Удаление истории выполнения"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            if instance_id:
                cursor.execute("DELETE FROM procHist WHERE instance_id = %s", (instance_id,))
            elif days_old:
                cursor.execute("DELETE FROM procHist WHERE started_at < NOW() - INTERVAL '%s days'", (days_old,))
            else:
                cursor.execute("DELETE FROM procHist")

            conn.commit()
            return cursor.rowcount
        except Exception as e:
            print(f"Ошибка при удалении истории: {e}")
            conn.rollback()
            return 0
        finally:
            cursor.close()
            self.return_connection(conn)


# Глобальный экземпляр БД
db = Database()