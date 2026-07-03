"""
Flask Web 看板 — 工商银行为主的舆情可视化
"""
import os
import sys
from flask import Flask, render_template, jsonify, request

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from storage.db import get_stats, get_articles, get_banks, get_daily_articles, get_monthly_summary, get_articles_by_month, init_db

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats")
def api_stats():
    bank = request.args.get("bank", "")
    date = request.args.get("date", "")
    time_range = request.args.get("time_range", "")
    return jsonify(get_stats(bank=bank, date=date, time_range=time_range))


@app.route("/api/articles")
def api_articles():
    bank = request.args.get("bank", "")
    keyword = request.args.get("keyword", "")
    source = request.args.get("source", "")
    sentiment = request.args.get("sentiment", "")
    date = request.args.get("date", "")
    time_range = request.args.get("time_range", "")
    limit = request.args.get("limit", 500, type=int)
    offset = request.args.get("offset", 0, type=int)

    articles = get_articles(
        bank=bank, keyword=keyword, source=source,
        sentiment=sentiment, date=date, time_range=time_range,
        limit=limit, offset=offset,
    )
    return jsonify(articles)


@app.route("/api/banks")
def api_banks():
    return jsonify(get_banks())


@app.route("/api/daily")
def api_daily():
    """获取某银行某日的文章，按来源+词条分组"""
    bank = request.args.get("bank", "工商银行")
    date = request.args.get("date", "")
    return jsonify(get_daily_articles(bank=bank, date=date))


@app.route("/api/today")
def api_today():
    """获取全部银行今日数据（用于首屏概览）"""
    from datetime import date as dt_date
    today = dt_date.today().strftime("%Y-%m-%d")
    stats = get_stats(date=today)
    banks_summary = stats["by_bank"]
    return jsonify({
        "date": today,
        "banks": banks_summary,
        "total": stats["total"],
    })


@app.route("/api/monthly")
def api_monthly():
    """获取月度舆情总结"""
    bank = request.args.get("bank", "")
    time_range = request.args.get("time_range", "")
    return jsonify(get_monthly_summary(bank=bank, time_range=time_range))


@app.route("/api/month/<month>")
def api_month_detail(month):
    """获取某月的详细文章列表"""
    bank = request.args.get("bank", "")
    articles = get_articles_by_month(bank=bank, month=month)
    return jsonify(articles)


def run_dashboard(host="0.0.0.0", port=5000):
    init_db()
    print(f"\n{'='*50}")
    print(f"  舆情监测看板已启动")
    print(f"  访问地址: http://127.0.0.1:{port}")
    print(f"{'='*50}\n")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    run_dashboard()
