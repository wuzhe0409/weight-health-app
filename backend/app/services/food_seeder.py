"""Seed the food_library table with common Chinese foods (idempotent)."""
from __future__ import annotations

from sqlmodel import Session, select

from app.models import FoodLibraryItem

# Category mapping: staple/meat/veg/fruit/snack/drink/dairy/other
SEED_FOODS = [
    # ── 主食 staple ──
    {"name": "白米饭", "category": "staple", "cal_per_100g": 116, "protein": 2.6, "carbs": 25.9, "fat": 0.3, "portion": "1碗(150g)", "portion_g": 150, "portion_kcal": 174},
    {"name": "馒头", "category": "staple", "cal_per_100g": 223, "protein": 7.0, "carbs": 44.2, "fat": 1.1, "portion": "1个(100g)", "portion_g": 100, "portion_kcal": 223},
    {"name": "面条（煮）", "category": "staple", "cal_per_100g": 110, "protein": 3.5, "carbs": 22.0, "fat": 0.5, "portion": "1碗(250g)", "portion_g": 250, "portion_kcal": 275},
    {"name": "全麦面包", "category": "staple", "cal_per_100g": 246, "protein": 10.0, "carbs": 43.0, "fat": 3.0, "portion": "1片(40g)", "portion_g": 40, "portion_kcal": 98},
    {"name": "小米粥", "category": "staple", "cal_per_100g": 46, "protein": 1.4, "carbs": 8.4, "fat": 0.7, "portion": "1碗(300g)", "portion_g": 300, "portion_kcal": 138},
    {"name": "红薯", "category": "staple", "cal_per_100g": 86, "protein": 1.6, "carbs": 20.1, "fat": 0.1, "portion": "1个(200g)", "portion_g": 200, "portion_kcal": 172},
    {"name": "玉米", "category": "staple", "cal_per_100g": 112, "protein": 4.0, "carbs": 22.8, "fat": 1.2, "portion": "1根(200g)", "portion_g": 200, "portion_kcal": 224},
    {"name": "燕麦片", "category": "staple", "cal_per_100g": 377, "protein": 13.5, "carbs": 61.6, "fat": 6.7, "portion": "1份(40g)", "portion_g": 40, "portion_kcal": 151},
    {"name": "饺子（猪肉白菜）", "category": "staple", "cal_per_100g": 240, "protein": 8.0, "carbs": 28.0, "fat": 10.0, "portion": "10个(200g)", "portion_g": 200, "portion_kcal": 480},

    # ── 肉类 meat ──
    {"name": "鸡胸肉", "category": "meat", "cal_per_100g": 133, "protein": 31.0, "carbs": 0.0, "fat": 1.2, "portion": "1块(150g)", "portion_g": 150, "portion_kcal": 200},
    {"name": "鸡腿肉（去皮）", "category": "meat", "cal_per_100g": 119, "protein": 20.0, "carbs": 0.0, "fat": 4.0, "portion": "1只(100g)", "portion_g": 100, "portion_kcal": 119},
    {"name": "猪瘦肉", "category": "meat", "cal_per_100g": 143, "protein": 20.3, "carbs": 1.5, "fat": 6.2, "portion": "1份(100g)", "portion_g": 100, "portion_kcal": 143},
    {"name": "猪排骨", "category": "meat", "cal_per_100g": 264, "protein": 18.0, "carbs": 0.0, "fat": 20.0, "portion": "1份(100g)", "portion_g": 100, "portion_kcal": 264},
    {"name": "牛腱子", "category": "meat", "cal_per_100g": 122, "protein": 20.1, "carbs": 0.2, "fat": 4.8, "portion": "1份(100g)", "portion_g": 100, "portion_kcal": 122},
    {"name": "牛肉（肥牛）", "category": "meat", "cal_per_100g": 250, "protein": 15.0, "carbs": 0.0, "fat": 21.0, "portion": "1份(100g)", "portion_g": 100, "portion_kcal": 250},
    {"name": "虾仁", "category": "meat", "cal_per_100g": 48, "protein": 10.4, "carbs": 0.4, "fat": 0.5, "portion": "1份(100g)", "portion_g": 100, "portion_kcal": 48},
    {"name": "三文鱼", "category": "meat", "cal_per_100g": 208, "protein": 20.0, "carbs": 0.0, "fat": 13.0, "portion": "1块(120g)", "portion_g": 120, "portion_kcal": 250},
    {"name": "鸡蛋（煮）", "category": "meat", "cal_per_100g": 144, "protein": 13.3, "carbs": 1.5, "fat": 8.8, "portion": "1个(50g)", "portion_g": 50, "portion_kcal": 72},

    # ── 蔬菜 veg ──
    {"name": "西兰花", "category": "veg", "cal_per_100g": 36, "protein": 4.1, "carbs": 4.3, "fat": 0.6, "portion": "1份(200g)", "portion_g": 200, "portion_kcal": 72},
    {"name": "菠菜", "category": "veg", "cal_per_100g": 28, "protein": 3.0, "carbs": 2.0, "fat": 0.3, "portion": "1份(200g)", "portion_g": 200, "portion_kcal": 56},
    {"name": "番茄", "category": "veg", "cal_per_100g": 19, "protein": 0.9, "carbs": 3.5, "fat": 0.2, "portion": "1个(150g)", "portion_g": 150, "portion_kcal": 29},
    {"name": "黄瓜", "category": "veg", "cal_per_100g": 16, "protein": 0.8, "carbs": 2.9, "fat": 0.2, "portion": "1根(200g)", "portion_g": 200, "portion_kcal": 32},
    {"name": "生菜", "category": "veg", "cal_per_100g": 15, "protein": 1.0, "carbs": 2.0, "fat": 0.1, "portion": "1份(100g)", "portion_g": 100, "portion_kcal": 15},
    {"name": "白菜", "category": "veg", "cal_per_100g": 17, "protein": 1.2, "carbs": 2.8, "fat": 0.1, "portion": "1份(200g)", "portion_g": 200, "portion_kcal": 34},
    {"name": "胡萝卜", "category": "veg", "cal_per_100g": 37, "protein": 1.0, "carbs": 7.7, "fat": 0.2, "portion": "1根(150g)", "portion_g": 150, "portion_kcal": 56},
    {"name": "土豆", "category": "veg", "cal_per_100g": 81, "protein": 2.0, "carbs": 17.0, "fat": 0.2, "portion": "1个(150g)", "portion_g": 150, "portion_kcal": 122},
    {"name": "菌菇（香菇）", "category": "veg", "cal_per_100g": 26, "protein": 2.2, "carbs": 3.3, "fat": 0.3, "portion": "1份(100g)", "portion_g": 100, "portion_kcal": 26},
    {"name": "豆腐", "category": "veg", "cal_per_100g": 76, "protein": 8.1, "carbs": 2.0, "fat": 3.7, "portion": "1块(200g)", "portion_g": 200, "portion_kcal": 152},

    # ── 水果 fruit ──
    {"name": "苹果", "category": "fruit", "cal_per_100g": 53, "protein": 0.2, "carbs": 13.8, "fat": 0.2, "portion": "1个(200g)", "portion_g": 200, "portion_kcal": 106},
    {"name": "香蕉", "category": "fruit", "cal_per_100g": 93, "protein": 1.1, "carbs": 20.8, "fat": 0.2, "portion": "1根(120g)", "portion_g": 120, "portion_kcal": 112},
    {"name": "橙子", "category": "fruit", "cal_per_100g": 48, "protein": 0.8, "carbs": 10.6, "fat": 0.2, "portion": "1个(200g)", "portion_g": 200, "portion_kcal": 96},
    {"name": "葡萄", "category": "fruit", "cal_per_100g": 70, "protein": 0.5, "carbs": 16.0, "fat": 0.2, "portion": "1串(200g)", "portion_g": 200, "portion_kcal": 140},
    {"name": "西瓜", "category": "fruit", "cal_per_100g": 31, "protein": 0.6, "carbs": 6.8, "fat": 0.1, "portion": "1块(300g)", "portion_g": 300, "portion_kcal": 93},
    {"name": "蓝莓", "category": "fruit", "cal_per_100g": 57, "protein": 0.7, "carbs": 14.0, "fat": 0.3, "portion": "1盒(125g)", "portion_g": 125, "portion_kcal": 71},
    {"name": "草莓", "category": "fruit", "cal_per_100g": 32, "protein": 0.7, "carbs": 7.7, "fat": 0.3, "portion": "10颗(200g)", "portion_g": 200, "portion_kcal": 64},

    # ── 零食小吃 snack ──
    {"name": "坚果（杏仁）", "category": "snack", "cal_per_100g": 579, "protein": 21.2, "carbs": 19.7, "fat": 49.9, "portion": "1小把(20g)", "portion_g": 20, "portion_kcal": 116},
    {"name": "酸奶（原味）", "category": "snack", "cal_per_100g": 72, "protein": 2.5, "carbs": 9.3, "fat": 2.7, "portion": "1杯(150g)", "portion_g": 150, "portion_kcal": 108},
    {"name": "黑巧克力（70%）", "category": "snack", "cal_per_100g": 545, "protein": 7.8, "carbs": 34.0, "fat": 42.6, "portion": "2块(20g)", "portion_g": 20, "portion_kcal": 109},
    {"name": "薯片", "category": "snack", "cal_per_100g": 536, "protein": 7.0, "carbs": 50.0, "fat": 34.0, "portion": "1小包(40g)", "portion_g": 40, "portion_kcal": 214},
    {"name": "饼干", "category": "snack", "cal_per_100g": 435, "protein": 8.0, "carbs": 65.0, "fat": 16.0, "portion": "3片(30g)", "portion_g": 30, "portion_kcal": 131},
    {"name": "辣条", "category": "snack", "cal_per_100g": 450, "protein": 8.0, "carbs": 48.0, "fat": 25.0, "portion": "1小包(30g)", "portion_g": 30, "portion_kcal": 135},
    {"name": "牛肉干", "category": "snack", "cal_per_100g": 308, "protein": 55.6, "carbs": 5.0, "fat": 8.0, "portion": "1小包(20g)", "portion_g": 20, "portion_kcal": 62},

    # ── 饮品 drink ──
    {"name": "牛奶（全脂）", "category": "drink", "cal_per_100g": 65, "protein": 3.2, "carbs": 4.8, "fat": 3.6, "portion": "1杯(250ml)", "portion_g": 250, "portion_kcal": 163},
    {"name": "豆浆（无糖）", "category": "drink", "cal_per_100g": 31, "protein": 3.0, "carbs": 1.2, "fat": 1.4, "portion": "1杯(250ml)", "portion_g": 250, "portion_kcal": 78},
    {"name": "美式咖啡", "category": "drink", "cal_per_100g": 2, "protein": 0.1, "carbs": 0.0, "fat": 0.0, "portion": "1杯(350ml)", "portion_g": 350, "portion_kcal": 7},
    {"name": "拿铁咖啡", "category": "drink", "cal_per_100g": 45, "protein": 2.0, "carbs": 4.0, "fat": 2.5, "portion": "1杯(350ml)", "portion_g": 350, "portion_kcal": 158},
    {"name": "可乐", "category": "drink", "cal_per_100g": 42, "protein": 0, "carbs": 10.6, "fat": 0, "portion": "1罐(330ml)", "portion_g": 330, "portion_kcal": 139},
    {"name": "奶茶（珍珠）", "category": "drink", "cal_per_100g": 70, "protein": 1.5, "carbs": 12.0, "fat": 2.0, "portion": "1杯(500ml)", "portion_g": 500, "portion_kcal": 350},
    {"name": "椰子水", "category": "drink", "cal_per_100g": 19, "protein": 0.0, "carbs": 3.7, "fat": 0.2, "portion": "1杯(300ml)", "portion_g": 300, "portion_kcal": 57},

    # ── 乳制品/调味品 dairy ──
    {"name": "奶酪片", "category": "dairy", "cal_per_100g": 350, "protein": 25.0, "carbs": 1.0, "fat": 27.0, "portion": "1片(20g)", "portion_g": 20, "portion_kcal": 70},
    {"name": "黄油", "category": "dairy", "cal_per_100g": 730, "protein": 0.5, "carbs": 0.1, "fat": 82.0, "portion": "1小块(10g)", "portion_g": 10, "portion_kcal": 73},

    # ── 其他 other ──
    {"name": "火锅（麻辣锅底）", "category": "other", "cal_per_100g": 150, "protein": 8.0, "carbs": 3.0, "fat": 12.0, "portion": "1人份(500g)", "portion_g": 500, "portion_kcal": 750},
    {"name": "麻辣烫（清汤）", "category": "other", "cal_per_100g": 60, "protein": 4.0, "carbs": 4.0, "fat": 3.0, "portion": "1份(400g)", "portion_g": 400, "portion_kcal": 240},
    {"name": "沙拉（油醋汁）", "category": "other", "cal_per_100g": 45, "protein": 2.0, "carbs": 3.0, "fat": 2.5, "portion": "1份(300g)", "portion_g": 300, "portion_kcal": 135},
    {"name": "方便面", "category": "other", "cal_per_100g": 473, "protein": 10.0, "carbs": 60.0, "fat": 22.0, "portion": "1包(100g)", "portion_g": 100, "portion_kcal": 473},
    {"name": "寿司（三文鱼）", "category": "other", "cal_per_100g": 150, "protein": 6.0, "carbs": 22.0, "fat": 4.0, "portion": "6个(180g)", "portion_g": 180, "portion_kcal": 270},

    # 中式菜肴
    {"name": "西红柿炒鸡蛋", "category": "other", "cal_per_100g": 85, "protein": 5.0, "carbs": 3.0, "fat": 6.0, "portion": "1份(250g)", "portion_g": 250, "portion_kcal": 213},
    {"name": "宫保鸡丁", "category": "other", "cal_per_100g": 178, "protein": 15.0, "carbs": 8.0, "fat": 10.0, "portion": "1份(200g)", "portion_g": 200, "portion_kcal": 356},
    {"name": "清蒸鱼", "category": "other", "cal_per_100g": 105, "protein": 17.0, "carbs": 0.0, "fat": 4.0, "portion": "1条(300g)", "portion_g": 300, "portion_kcal": 315},
    {"name": "红烧肉", "category": "other", "cal_per_100g": 305, "protein": 10.0, "carbs": 3.0, "fat": 28.0, "portion": "1份(150g)", "portion_g": 150, "portion_kcal": 458},
    {"name": "麻婆豆腐", "category": "other", "cal_per_100g": 100, "protein": 6.0, "carbs": 4.0, "fat": 7.0, "portion": "1份(200g)", "portion_g": 200, "portion_kcal": 200},
]


def seed_food_library(session: Session) -> int:
    """Insert seed foods if table is empty. Returns count of newly inserted items."""
    existing = session.exec(select(FoodLibraryItem).limit(1)).first()
    if existing:
        return 0

    count = 0
    for f in SEED_FOODS:
        item = FoodLibraryItem(
            name=f["name"],
            category=f["category"],
            calories_per_100g=f["cal_per_100g"],
            protein_per_100g=f["protein"],
            carbs_per_100g=f["carbs"],
            fat_per_100g=f["fat"],
            common_portion=f["portion"],
            common_portion_g=f["portion_g"],
            common_portion_kcal=f["portion_kcal"],
        )
        session.add(item)
        count += 1
    session.commit()
    return count
