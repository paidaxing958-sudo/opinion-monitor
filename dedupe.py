#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按 (bank, title) 去重，保留每组最新的（crawled_at 最大）一条。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.db import get_connection


def main():
    conn = get_connection()
    cur = conn.cursor()
    before = cur.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    print(f"Before: {before} rows")

    # 删除 (bank, title) 重复，保留 crawled_at 最大的那条（id 最大也行）
    cur.execute("""
        DELETE FROM articles
        WHERE id NOT IN (
            SELECT MAX(id) FROM articles
            WHERE title IS NOT NULL AND title != ''
            GROUP BY bank, title
        )
        AND title IS NOT NULL AND title != ''
    """)
    deleted1 = cur.rowcount
    print(f"Deleted (by title): {deleted1}")

    # 剩余可能还有 title 为空的，按 url 去重
    cur.execute("""
        DELETE FROM articles
        WHERE id NOT IN (
            SELECT MAX(id) FROM articles
            GROUP BY bank, url
        )
    """)
    deleted2 = cur.rowcount
    print(f"Deleted (by url): {deleted2}")

    conn.commit()
    after = cur.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    print(f"After: {after} rows  (removed {before - after})")

    # 按月分布
    cur.execute("""
        SELECT substr(published_at, 1, 7) as m, bank, COUNT(*)
        FROM articles
        WHERE length(published_at) >= 10 AND substr(published_at, 5, 1) = '-'
        GROUP BY m, bank ORDER BY m, bank
    """)
    print("Distribution:")
    for r in cur.fetchall():
        print(" ", r)
    conn.close()


if __name__ == "__main__":
    main()
