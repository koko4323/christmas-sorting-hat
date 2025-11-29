# -*- coding: utf-8 -*-
import streamlit as st
import random
import time
import io
import csv
import json
import os

AGE_GROUPS = ["低年級", "中年級", "高年級", "國中以上"]
STATE_FILE = "sorting_hat_state.json"

st.set_page_config(page_title="聖誕節分類帽系統", layout="wide")

# ---- 全域按鈕變大一點（含分類鍵）----
st.markdown(
    """
    <style>
    div.stButton > button {
        font-size: 1.4rem;
        padding: 0.8rem 2.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ========= 狀態存取 =========
def save_state():
    data = {
        "theme": st.session_state.theme,
        "team_count": st.session_state.team_count,
        "team_size": st.session_state.team_size,
        "team_names": st.session_state.team_names,
        "balance_age": st.session_state.balance_age,
        "require_name": st.session_state.require_name,
        "students": st.session_state.students,
    }
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # 寫檔失敗就算了，避免影響前端


def load_state():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ========= 建隊工具 =========
def rebuild_teams():
    """依照 team_names + students 重建 teams 結構"""
    team_names = st.session_state.team_names
    teams = [{"name": name, "members": []} for name in team_names]
    name_to_idx = {t["name"]: i for i, t in enumerate(teams)}

    for stu in st.session_state.students:
        t_name = stu["team"]
        idx = name_to_idx.get(t_name)
        if idx is not None:
            teams[idx]["members"].append(
                {"name": stu["name"], "age_group": stu["age_group"]}
            )

    st.session_state.teams = teams


def ensure_team_names_length():
    """確保 team_names 長度跟 team_count 一致"""
    tc = int(st.session_state.team_count)
    names = st.session_state.team_names

    if len(names) < tc:
        for i in range(len(names), tc):
            names.append(f"第{i+1}隊")
    elif len(names) > tc:
        names = names[:tc]

    st.session_state.team_names = names


def reset_all(clear_students=True):
    """重建隊伍；必要時清空分配紀錄"""
    ensure_team_names_length()
    if clear_students:
        st.session_state.students = []
        st.session_state.last_assignment = None
    rebuild_teams()
    save_state()


# ========= 分隊邏輯 =========
def choose_team_for_student(age_group: str):
    teams = st.session_state.teams
    max_size = int(st.session_state.team_size)

    if not teams:
        return None

    if all(len(t["members"]) >= max_size for t in teams):
        return None

    if not st.session_state.balance_age:
        candidates = []
        for idx, team in enumerate(teams):
            if len(team["members"]) >= max_size:
                continue
            total = len(team["members"])
            candidates.append((idx, total))
        if not candidates:
            return None
        min_total = min(c[1] for c in candidates)
        candidates = [c for c in candidates if c[1] == min_total]
        return random.choice(candidates)[0]

    candidates = []
    for idx, team in enumerate(teams):
        if len(team["members"]) >= max_size:
            continue
        same_age = sum(1 for m in team["members"] if m["age_group"] == age_group)
        total = len(team["members"])
        candidates.append((idx, same_age, total))

    if not candidates:
        return None

    min_age = min(c[1] for c in candidates)
    candidates = [c for c in candidates if c[1] == min_age]

    min_total = min(c[2] for c in candidates)
    candidates = [c for c in candidates if c[2] == min_total]

    return random.choice(candidates)[0]


def update_student_team_summary():
    teams = st.session_state.teams
    try:
        max_size = int(st.session_state.team_size)
    except ValueError:
        max_size = 0

    lines = []
    for t in teams:
        lines.append(f"{t['name']}：{len(t['members'])} / {max_size} 人")
    return "\n".join(lines)


def build_log_csv():
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["序號", "姓名", "年齡級距", "隊伍名稱"])
    for idx, stu in enumerate(st.session_state.students, start=1):
        writer.writerow([idx, stu["name"], stu["age_group"], stu["team"]])
    return buf.getvalue().encode("utf-8-sig")


# ========= 初始化 =========
def init_state():
    if "initialized" in st.session_state:
        return

    st.session_state.initialized = True
    st.session_state.theme = "聖誕節分類帽分組系統"
    st.session_state.team_count = 3
    st.session_state.team_size = 100
    st.session_state.balance_age = True
    st.session_state.require_name = True
    st.session_state.team_names = ["麋鹿隊", "雪人隊", "聖誕樹隊"]
    st.session_state.students = []
    st.session_state.teams = []
    st.session_state.last_assignment = None

    # 嘗試從本地檔案載入舊狀態
    data = load_state()
    if data:
        st.session_state.theme = data.get("theme", st.session_state.theme)
        st.session_state.team_count = int(data.get("team_count", 3))
        st.session_state.team_size = int(data.get("team_size", 100))
        st.session_state.team_names = data.get(
            "team_names",
            st.session_state.team_names,
        )
        st.session_state.balance_age = bool(data.get("balance_age", True))
        st.session_state.require_name = bool(data.get("require_name", True))
        st.session_state.students = data.get("students", [])

    ensure_team_names_length()
    rebuild_teams()


# ========= 主程式 =========
init_state()

st.title("🎄 聖誕節分類帽系統（Streamlit 版）")

tab_student, tab_teacher = st.tabs(["🎓 學生畫面", "🧑‍🏫 老師後台"])

# ================== 學生畫面 ==================
with tab_student:
    st.subheader("學生畫面")

    col_left, col_right = st.columns([1, 1.2])

    with col_left:
        st.markdown("#### 輸入資訊")
        name_label = "姓名（必填）" if st.session_state.require_name else "姓名（可留白）"
        name = st.text_input(name_label)
        age = st.selectbox("年齡級距", AGE_GROUPS, key="student_age")

        if st.button("🎩 分類！", key="sort_button"):
            raw_name = name.strip()

            if st.session_state.require_name and not raw_name:
                st.warning("老師有設定需要填姓名喔～請先輸入姓名再按分類。")
            else:
                idx = choose_team_for_student(age)
                if idx is None:
                    st.error("所有隊伍都已滿，無法再分配。")
                else:
                    display_name = raw_name if raw_name else "這位勇者"
                    placeholder = st.empty()
                    team_names = [t["name"] for t in st.session_state.teams]

                    spins = 18
                    for k in range(spins):
                        showing = team_names[k % len(team_names)]
                        placeholder.markdown(
                            f"""
                            <div style="
                                text-align: center;
                                padding: 40px 20px;
                                border-radius: 24px;
                                border: 6px solid #FACC15;
                                background-color: #020617;
                                color: #F9FAFB;
                                margin-top: 20px;
                            ">
                                <div style="font-size: 3rem; font-weight: 800; margin-bottom: 24px;">
                                    {display_name}
                                </div>
                                <div style="font-size: 2.4rem; margin-bottom: 16px;">
                                    你被分到……
                                </div>
                                <div style="font-size: 3rem; font-weight: 800; color: #FACC15; margin-top: 16px;">
                                    
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        time.sleep(0.08)

                    # 真正確定的隊伍
                    team = st.session_state.teams[idx]
                    member = {"name": display_name, "age_group": age}
                    team["members"].append(member)
                    st.session_state.students.append(
                        {"name": display_name, "age_group": age, "team": team["name"]}
                    )
                    st.session_state.last_assignment = {
                        "name": display_name,
                        "team": team["name"],
                    }

                    # 最終畫面（確定隊名）
                    card_html = f"""
                    <div style="
                        text-align: center;
                        padding: 40px 20px;
                        border-radius: 24px;
                        border: 6px solid #FACC15;
                        background-color: #020617;
                        color: #F9FAFB;
                        margin-top: 20px;
                    ">
                        <div style="font-size: 3rem; font-weight: 800; margin-bottom: 24px;">
                            {display_name}
                        </div>
                        <div style="font-size: 2.4rem; margin-bottom: 16px;">
                            你被分到……
                        </div>
                        <div style="font-size: 3.2rem; font-weight: 800; color: #F97316; margin-top: 16px;">
                            
                        </div>
                        <div style="font-size: 2.5rem; margin-top: 16px;">
                            🎉
                        </div>
                    </div>
                    """
                    placeholder.markdown(card_html, unsafe_allow_html=True)

                    # 存檔，防止重整消失
                    save_state()

    with col_right:
        st.markdown("#### 分類結果顯示區")
        if st.session_state.last_assignment:
            last = st.session_state.last_assignment
            st.markdown(
                f"## 最近一次分配\n\n**{last['name']}** 被分到 👉 **{last['team']}**"
            )
        else:
            st.info("目前尚未有任何分配。")

        st.markdown("#### 各隊目前人數")
        summary_text = update_student_team_summary()
        st.text(summary_text if summary_text else "尚未建立隊伍。")


# ================== 老師後台 ==================
with tab_teacher:
    st.subheader("老師後台設定與紀錄")

    st.markdown("### 系統設定")

    c1, c2, c3 = st.columns([2, 2, 2])

    with c1:
        st.session_state.theme = st.text_input(
            "主題名稱",
            value=st.session_state.theme,
        )

    with c2:
        st.session_state.team_count = st.number_input(
            "隊伍數量",
            min_value=1,
            max_value=20,
            value=int(st.session_state.team_count),
            step=1,
        )

    with c3:
        st.session_state.team_size = st.number_input(
            "每隊上限人數",
            min_value=1,
            max_value=500,
            value=int(st.session_state.team_size),
            step=1,
        )

    # 隊伍名稱：一隊一欄
    st.markdown("#### 隊伍名稱設定")
    ensure_team_names_length()
    new_names = []
    for i in range(int(st.session_state.team_count)):
        default = st.session_state.team_names[i]
        name_input = st.text_input(
            f"隊伍 {i+1} 名稱",
            value=default,
            key=f"team_name_{i}",
        )
        name_input = name_input.strip() or f"第{i+1}隊"
        new_names.append(name_input)
    st.session_state.team_names = new_names

    st.session_state.balance_age = st.checkbox(
        "平均分散各年齡層到各隊（建議勾選）",
        value=st.session_state.balance_age,
    )

    st.session_state.require_name = st.checkbox(
        "分組時必須輸入姓名",
        value=st.session_state.require_name,
        help="取消勾選後，學生可以不記名分組。",
    )

    col_btn1, col_btn2 = st.columns([1, 1])

    with col_btn1:
        if st.button("套用設定並重設隊伍（清空分配）"):
            reset_all(clear_students=True)
            st.success("已依照目前設定重設隊伍並清空分配紀錄。")

    with col_btn2:
        if st.session_state.students:
            csv_data = build_log_csv()
            st.download_button(
                label="下載分組 Log（CSV）",
                data=csv_data,
                file_name="sorting_log.csv",
                mime="text/csv",
            )
        else:
            st.info("目前沒有可下載的 Log（尚未有任何分配）。")

    st.markdown("---")

    # ===== 手動丟人進指定隊伍 =====
    st.markdown("### 手動加入指定隊伍")
    col_m1, col_m2, col_m3, col_m4 = st.columns([2, 2, 2, 2])

    with col_m1:
        manual_name = st.text_input("姓名（可留白）", key="manual_name")

    with col_m2:
        manual_age = st.selectbox(
            "年齡級距",
            AGE_GROUPS,
            key="manual_age_group",
        )

    with col_m3:
        team_options = [t["name"] for t in st.session_state.teams]
        manual_team = st.selectbox(
            "指定隊伍",
            team_options if team_options else ["尚未建立隊伍"],
            key="manual_team_select",
        )

    with col_m4:
        if st.button("手動加入隊伍"):
            if not st.session_state.teams:
                st.warning("目前尚未建立隊伍。")
            else:
                disp_name = manual_name.strip() or "這位勇者"
                stu = {
                    "name": disp_name,
                    "age_group": manual_age,
                    "team": manual_team,
                }
                st.session_state.students.append(stu)
                rebuild_teams()
                save_state()
                st.success(f"已將「{disp_name}」加入 {manual_team}。")

    st.markdown("---")

    col_log, col_team = st.columns(2)

    with col_log:
        st.markdown("### 已分類學生紀錄")
        if not st.session_state.students:
            st.info("尚無已分類學生。")
        else:
            lines = []
            for idx, stu in enumerate(st.session_state.students, start=1):
                lines.append(
                    f"{idx}. {stu['name']}（{stu['age_group']}）→ {stu['team']}"
                )
            st.text("\n".join(lines))

    with col_team:
        st.markdown("### 隊伍詳細狀態")
        teams = st.session_state.teams
        if not teams:
            st.info("尚未建立隊伍。")
        else:
            try:
                max_size = int(st.session_state.team_size)
            except ValueError:
                max_size = 0

            st.markdown(
                f"**總人數：** {len(st.session_state.students)}　｜　"
                f"**隊伍數：** {len(teams)}　｜　"
                f"**每隊上限：** {max_size}"
            )
            st.markdown("---")

            for t in teams:
                st.markdown(f"#### {t['name']}（{len(t['members'])} / {max_size} 人）")
                if not t["members"]:
                    st.write("（目前尚無成員）")
                else:
                    ordered = sorted(
                        t["members"],
                        key=lambda m: AGE_GROUPS.index(m["age_group"])
                        if m["age_group"] in AGE_GROUPS
                        else 99,
                    )
                    for m in ordered:
                        st.write(f"- {m['name']}（{m['age_group']}）")
                st.markdown("---")
