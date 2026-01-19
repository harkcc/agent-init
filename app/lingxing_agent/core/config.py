# 店铺负责人映射
PROJECT_MANNER = {
    "BT-US": "陈钰",
    "BT-CA": "陈钰",
    "AC-US": "郑海燕",
    "AC-CA": "郑海燕",
    "JPD-JP": "何清霞",
    "JPE-JP": "何清霞",
    "WMBT-US": "余丽洁",
    "BN-US": "林琳",
    "BN-CA": "林琳",
    "DK-UK": "唐盈婷",
    "DK-IT": "唐盈婷",
    "HB-US": "杨莹",
    "HB-CA": "杨莹",
    "DK-DE": "黄雨欣",
    "DK-FR": "黄雨欣",
    "OP-UK": "刘燕菲",
    "YM-JP": "徐晓樱",
    "OP-FR": "111",
    "OP-IT": "111",
    "YM—UK": "111",
    "YM—DE": "111",
}

# 店铺 WID 映射
PROJECT_WID = {
    "BT-US": "507381",
    "BT-CA": "507382",
    "AC-US": "506304",
    "AC-CA": "506305",
    "JPD-JP": "507196",
    "JPE-JP": "507352",
    "BN-US": "507188",
    "BN-CA": "507189",
    "DK-UK": "508977",
    "DK-IT": "506313",
    "HB-US": "506307",
    "HB-CA": "506308",
    "DK-DE": "504768",
    "DK-FR": "504769",
    "OP-UK": "504704",
    "YM-JP": "516436",
    "OP-FR": "504707",
    "OP-IT": "504705",
    "YM-UK": "505460",
    "YM-DE": "505462",
}

# 店铺 SID 映射
PROJECT_SID = {
    "BT-US": "505674",
    "BT-CA": "505675",
    "AC-US": "504758",
    "AC-CA": "504759",
    "JPD-JP": "505540",
    "JPE-JP": "505654",
    "BN-US": "505533",
    "BN-CA": "505534",
    "DK-UK": "517160",
    "DK-IT": "504767",
    "HB-US": "504761",
    "HB-CA": "504762",
    "DK-DE": "506314",
    "DK-FR": "506315",
    "OP-UK": "506237",
    "YM-JP": "520747",
    "OP-FR": "506240",
    "OP-IT": "506238",
    "YM—UK": "507063",
    "YM—DE": "507065",
}


def get_store_id(store_name: str) -> str | None:
    """根据店名获取 SID，如果未找到尝试模糊匹配"""
    if store_name in PROJECT_SID:
        return PROJECT_SID[store_name]

    # 模糊匹配尝试
    for name, sid in PROJECT_SID.items():
        if store_name.upper() in name.upper():
            return sid
    return None


# 账号信息
ACCOUNT = "baitai-350000"
PWD = "Lx159357"
