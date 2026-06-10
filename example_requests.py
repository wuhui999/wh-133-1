import requests
import json
from datetime import datetime, timedelta

BASE = "http://localhost:8001"


def pp(label, r):
    print(f"\n=== {label} === [{r.status_code}]")
    try:
        print(json.dumps(r.json(), indent=2, ensure_ascii=False, default=str))
    except Exception:
        print(r.text)


s = requests.Session()

pp("1. 创建药企", s.post(f"{BASE}/api/auth/enterprises", json={"name": "恒瑞医药", "ent_type": "pharma"}))
pp("2. 创建承运商", s.post(f"{BASE}/api/auth/enterprises", json={"name": "顺丰冷运", "ent_type": "carrier"}))

r1 = s.post(f"{BASE}/api/auth/register", json={
    "username": "pharma_admin", "password": "123456", "role": "pharma", "enterprise_id": 1
})
pp("3. 注册药企用户", r1)

r2 = s.post(f"{BASE}/api/auth/register", json={
    "username": "carrier_admin", "password": "123456", "role": "carrier", "enterprise_id": 2
})
pp("4. 注册承运商用户", r2)

r3 = s.post(f"{BASE}/api/auth/register", json={
    "username": "supervisor", "password": "123456", "role": "supervisor"
})
pp("5. 注册监管员", r3)

login_r = s.post(f"{BASE}/api/auth/login", json={"username": "pharma_admin", "password": "123456"})
token = login_r.json()["access_token"]
s.headers.update({"Authorization": f"Bearer {token}"})
pp("6. 药企登录", login_r)

pp("7. 创建车辆", s.post(f"{BASE}/api/waybills/vehicles", json={"plate_number": "沪A12345", "carrier_id": 2}))
pp("8. 创建探头1", s.post(f"{BASE}/api/waybills/probes", json={"probe_code": "PROBE-001"}))
pp("9. 创建探头2", s.post(f"{BASE}/api/waybills/probes", json={"probe_code": "PROBE-002"}))

pp("10. 创建运单", s.post(f"{BASE}/api/waybills", json={
    "waybill_no": "WB-20260610-001",
    "drug_name": "新冠疫苗",
    "drug_type": "vaccine",
    "quantity": 1000,
    "pharma_enterprise_id": 1,
    "carrier_enterprise_id": 2,
    "vehicle_id": 1,
    "temp_min": 2.0,
    "temp_max": 8.0,
    "consecutive_exceed_limit_min": 5,
    "sampling_interval_sec": 60,
}))

pp("11. 绑定探头到运单", s.post(f"{BASE}/api/waybills/1/bind-probe", json={"probe_id": 1}))
pp("12. 绑定第二个探头", s.post(f"{BASE}/api/waybills/1/bind-probe", json={"probe_id": 2}))

now = datetime.utcnow()
loading_start = now - timedelta(hours=5)
loading_end = now - timedelta(hours=4, minutes=30)
departure = loading_end
arrival = now - timedelta(minutes=30)
unloading_start = arrival
unloading_end = now - timedelta(minutes=10)

pp("13. 更新运单状态为运输中", s.patch(f"{BASE}/api/waybills/1/status", json={
    "status": "in_transit",
    "loading_start": loading_start.isoformat(),
    "loading_end": loading_end.isoformat(),
    "departure_time": departure.isoformat(),
}))

t = loading_end + timedelta(minutes=1)
normal_samples = []
for i in range(20):
    normal_samples.append({
        "waybill_id": 1, "probe_id": 1,
        "temperature": 3.5 + (i % 3) * 0.5,
        "sampled_at": (t + timedelta(minutes=i)).isoformat(),
    })

pp("14. 批量写入正常温度采样", s.post(f"{BASE}/api/temperature/samples", json={"samples": normal_samples}))

exceed_start = t + timedelta(minutes=20)
exceed_samples = []
for i in range(7):
    exceed_samples.append({
        "waybill_id": 1, "probe_id": 1,
        "temperature": 10.5 + i * 0.3,
        "sampled_at": (exceed_start + timedelta(minutes=i)).isoformat(),
    })

pp("15. 写入超标温度采样(触发告警)", s.post(f"{BASE}/api/temperature/samples", json={"samples": exceed_samples}))

pp("16. 查询告警列表", s.get(f"{BASE}/api/alerts?waybill_id=1"))

pp("17. 查询温度曲线", s.get(f"{BASE}/api/temperature/curve/1"))

pp("18. 确认告警", s.post(f"{BASE}/api/alerts/1/confirm", json={"remark": "已确认温度超标"}))

pp("19. 处理告警", s.post(f"{BASE}/api/alerts/1/handle", json={"remark": "已联系承运商降温处理"}))

pp("20. 更新运单状态为已送达", s.patch(f"{BASE}/api/waybills/1/status", json={
    "status": "delivered",
    "arrival_time": arrival.isoformat(),
    "unloading_start": unloading_start.isoformat(),
    "unloading_end": unloading_end.isoformat(),
}))

pp("21. 生成责任段报告", s.post(f"{BASE}/api/responsibility/generate/1"))

pp("22. 查看责任段报告", s.get(f"{BASE}/api/responsibility/1"))

pp("23. 登记索赔", s.post(f"{BASE}/api/claims", json={
    "waybill_id": 1,
    "claimant_enterprise_id": 1,
    "respondent_enterprise_id": 2,
    "segment_id": 2,
    "alert_id": 1,
    "amount": 50000,
    "reason": "在途运输期间温度超标，导致疫苗效价下降",
}))

sup_login = s.post(f"{BASE}/api/auth/login", json={"username": "supervisor", "password": "123456"})
sup_token = sup_login.json()["access_token"]
s.headers.update({"Authorization": f"Bearer {sup_token}"})

pp("24. 审核索赔(通过)", s.post(f"{BASE}/api/claims/1/review", json={
    "status": "approved",
    "remark": "温度超标事实确认，承运商负主要责任",
}))

pp("25. 结案索赔", s.post(f"{BASE}/api/claims/1/close", json={
    "remark": "承运商已赔付，索赔结案",
}))

pp("26. 查询索赔详情", s.get(f"{BASE}/api/claims/1"))

pp("27. 查询审计日志", s.get(f"{BASE}/api/audit-logs"))

gap_samples = [
    {"waybill_id": 1, "probe_id": 2, "temperature": 4.0,
     "sampled_at": (now - timedelta(hours=3)).isoformat()},
    {"waybill_id": 1, "probe_id": 2, "temperature": 4.5,
     "sampled_at": (now - timedelta(hours=3, minutes=1)).isoformat()},
    {"waybill_id": 1, "probe_id": 2, "temperature": 3.8,
     "sampled_at": (now - timedelta(hours=1)).isoformat()},
]
s.headers.update({"Authorization": f"Bearer {token}"})
pp("28. 写入带间隔的采样(检测断点)", s.post(f"{BASE}/api/temperature/samples", json={"samples": gap_samples}))
pp("29. 检测采样断点", s.get(f"{BASE}/api/temperature/breakpoints/1/2"))

pp("30. 创建运单-胰岛素(不传温控参数，用默认值)", s.post(f"{BASE}/api/waybills", json={
    "waybill_no": "WB-INSULIN-001",
    "drug_name": "诺和灵R",
    "drug_type": "insulin",
    "quantity": 500,
    "pharma_enterprise_id": 1,
    "carrier_enterprise_id": 2,
}))

pp("31. 创建运单-生物制品(不传温控参数，用默认值)", s.post(f"{BASE}/api/waybills", json={
    "waybill_no": "WB-BIO-001",
    "drug_name": "单克隆抗体",
    "drug_type": "biologic",
    "quantity": 200,
    "pharma_enterprise_id": 1,
    "carrier_enterprise_id": 2,
}))

pp("32. 创建运单-疫苗(显式传参覆盖默认值)", s.post(f"{BASE}/api/waybills", json={
    "waybill_no": "WB-VAC-OVERRIDE-001",
    "drug_name": "HPV疫苗",
    "drug_type": "vaccine",
    "quantity": 300,
    "pharma_enterprise_id": 1,
    "carrier_enterprise_id": 2,
    "temp_min": 0.0,
    "temp_max": 5.0,
    "consecutive_exceed_limit_min": 3,
}))

pp("33. 验证运单列表(查看温控参数)", s.get(f"{BASE}/api/waybills"))

print("\n\n========== 全部示例请求执行完毕 ==========")
