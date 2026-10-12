# gohome

PC를 끌 때 G2Works 근태관리에 **퇴근**을 자동으로 찍는 상주 프로그램.

## 사용 방법 (직원용)
1. `gohome.exe`를 원하는 폴더에 두고 실행
   - 복사/설치 없이 그 자리에서 실행되며, 그 경로가 시작 프로그램에 등록됨 (exe를 옮기면 옮긴 곳에서 한 번 다시 실행)
   - 처음 실행하면 설정 창이 뜸 → 사번, 비밀번호, 퇴근 기준 시각 입력 → **로그인 확인 후 저장**
2. 이후에는 로그인할 때 자동으로 실행되어 트레이(작업 표시줄 오른쪽 아래)에 집 모양 아이콘으로 상주
3. **퇴근 기준 시각 이후에 PC를 종료하거나 재시작하면** 자동으로 퇴근을 찍음
   - 다시 찍으면 퇴근 시각이 마지막 시각으로 갱신됨
   - 로그아웃할 때는 찍지 않음
4. 실패하면 다음 로그인 때 알림 창이 뜸 (출근 기록이 없을 때 포함)

### 트레이 메뉴
| 메뉴 | 설명 |
|---|---|
| 설정 변경 | 사번/비밀번호/퇴근 기준 시각 변경 |
| 지금 퇴근 찍기 | 시각과 관계없이 바로 퇴근 처리 |
| 로그 폴더 열기 | 처리 기록 확인 |
| 프로그램 끄기 | 다음 로그인 전까지 동작 안 함 |
| 제거 | 시작 프로그램 해제 + 저장된 사번/비밀번호 삭제 (exe 폴더는 직접 삭제) |

### 주의
- 서명되지 않은 exe라서 처음 실행할 때 Windows SmartScreen이나 백신 경고가 뜰 수 있음
- 종료 화면에 "gohome / 퇴근 처리 중..."이 잠깐 보이면 정상 동작 중 ([그래도 종료]를 누르면 퇴근이 안 찍힘)

## 동작 원리
- 숨겨진 창으로 Windows 종료 신호(`WM_QUERYENDSESSION`)를 받아 종료를 잠깐 막고 퇴근 처리 후 종료를 계속 진행
- 종료 중에는 새 프로그램(브라우저 등)을 실행할 수 없어서, 브라우저 없이 HTTP로 직접 처리
  1. 로그인: `/g2works/login/ajaxLogin.do` (사번/비밀번호를 CryptoJS 방식 AES로 암호화, 사번 로그인)
  2. 상태 조회: `/g2works/main/attendInfo.json`
  3. 퇴근 요청: `/emp.auth.do?command=attendPostNew` (신규 근태) 또는 `attendPost1`, `kind=900788`
- 종료/재시작 구분은 이벤트 로그가 믿을 만하지 않아서 하지 않음 (기준 시각 이후면 무조건 찍음)
- 사번/비밀번호: Windows 자격 증명 관리자 `gohome-g2works`
- 로그, 실패 기록(`fail_flag.txt`), 설정(`config.json`): exe가 있는 폴더

## 개발
```powershell
python -m pip install -r requirements.txt
python app.py              # 소스로 실행 (시작 프로그램 등록 없음)
python app.py --settings   # 설정 창만
.\build.ps1                # dist\gohome.exe 생성
```

| 파일 | 역할 |
|---|---|
| `app.py` | 진입점, 트레이, 퇴근 처리 흐름 |
| `g2works.py` | G2Works 직접 통신 |
| `shutdown_hook.py` | 종료 신호 감지 |
| `credential.py` | 자격 증명 관리자 |
| `config.py` | 경로, 설정 |
| `installer.py` | 시작 프로그램 등록/해제, 제거 |
| `settings_ui.py` | 설정 창 |
| `icon.py` | 아이콘 |
