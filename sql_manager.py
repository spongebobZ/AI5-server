import mysql.connector
from cfg import config


def select(table, *columns, **condition):
    """
    :param table:
    :param columns:
    :param condition:
    :return:
    """
    conn = mysql.connector.connect(host=config.db_host, user=config.db_user, password=config.db_pwd,
                                   database=config.ai_db)
    cursor = conn.cursor()
    cols = columns and ','.join(columns) or '*'
    sql = 'select %s from %s' % (cols, table)
    if condition:
        sql += ' where'
        for k, v in condition.items():
            sql += isinstance(v, str) and ' %s=\'%s\' and' % (k, v) or ' %s=%s and' % (k, v)
        sql = sql[:-4]
    cursor.execute(sql)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


def insert(table, **values):
    """
    :param table:
    :param values:
    :return:
    """
    conn = mysql.connector.connect(host=config.db_host, user=config.db_user, password=config.db_pwd,
                                   database=config.ai_db)
    cursor = conn.cursor()
    key_list = ','.join(values.keys())
    value_list = ','.join(map(lambda x: isinstance(x, str) and '\'' + x + '\'' or str(x), values.values()))
    sql = 'insert into %s (%s) values (%s)' % (table, key_list, value_list)
    cursor.execute(sql)
    effect_rows = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()
    return effect_rows


def update(table, values, **condition):
    """
    :param table:
    :param values:
    :param condition:
    :return:
    """
    conn = mysql.connector.connect(host=config.db_host, user=config.db_user, password=config.db_pwd,
                                   database=config.ai_db)
    cursor = conn.cursor()
    kvs = ''
    for k, v in values.items():
        kvs += isinstance(v, str) and '%s=\'%s\',' % (k, v) or '%s=%s,' % (k, v)
    kvs = kvs[:-1]
    sql = 'update %s set %s' % (table, kvs)
    if condition:
        sql += ' where'
        for k, v in condition.items():
            sql += isinstance(v, str) and ' %s=\'%s\' and' % (k, v) or ' %s=%s and' % (k, v)
        sql = sql[:-4]
    cursor.execute(sql)
    effect_rows = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()
    return effect_rows


def delete(table, **condition):
    """
    :param table:
    :param condition:
    :return:
    """
    conn = mysql.connector.connect(host=config.db_host, user=config.db_user, password=config.db_pwd,
                                   database=config.ai_db)
    cursor = conn.cursor()
    sql = 'delete from %s' % table
    if condition:
        sql += ' where'
        for k, v in condition.items():
            sql += isinstance(v, str) and ' %s=\'%s\' and ' % (k, v) or ' %s=%s and' % (k, v)
        sql = sql[:-4]
    cursor.execute(sql)
    effect_rows = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()
    return effect_rows
