# 데이터베이스 디텍티브 한글패치

Steam 게임 **Database Detective: Minor Crimes Division** (Thomas Hsu)의 비공식 한글패치.
화면 문구와 대사뿐 아니라 **사진 단서와 사용 설명서 23쪽까지 그림째 다시 그려** 넣는다.
덤으로 원래 게임에 있던 **쿼리창 Enter 줄바꿈 버그**도 고친다.

BepInEx 플러그인으로 동작하며 **게임 원본 파일은 하나도 수정하지 않는다.**

## 받기

**[최신판 내려받기](https://github.com/krPlatypus/Database-Detective-Korean-Patch/releases/latest)**

1. `DDKoreanPatch-v1.0.1.zip`을 받는다
2. 스팀 라이브러리에서 게임 오른쪽 클릭 → 관리 → **로컬 파일 보기**
3. 압축을 그 폴더(`copOS.exe`가 있는 곳)에 **전부 풀어 넣는다**

지우려면 `winhttp.dll`, `doorstop_config.ini`, `.doorstop_version`, `changelog.txt`,
`BepInEx` 폴더만 지우면 된다. 자세한 설명은 압축 파일 안의 `읽어주세요.txt`에 있다.

번역이 어색한 곳을 보시면 [이슈](https://github.com/krPlatypus/Database-Detective-Korean-Patch/issues)로
알려 주십시오.

---

아래는 이 패치를 어떻게 만들었는지에 대한 기록이다.

## 구성

| 경로 | 내용 |
|---|---|
| `src/DDKoreanPatch/` | BepInEx 플러그인 (C#) |
| `tools/` | 애셋 분석·텍스트 추출·그림 제작 스크립트 (Python) |
| `translation/` | 번역 작업 파일 (사람이 편집) |
| `translation/images/` | 그림 편집 사양 (JSON) |
| `dist/` | 플러그인이 읽는 번들 — `translation.json`, `images/`, `fonts/`, `sounds/` |
| `extracted/` | 추출 원본 (git 제외) |
| `decompiled/` | 디컴파일 결과 (git 제외) |

## 게임 환경

- Unity **6000.5.5f1**, 스크립팅 백엔드 **Mono**
- BepInEx **5.4.23.5** + HarmonyX
- 로컬라이제이션 프레임워크 없음 (영어 하드코딩)
- 내장 폰트 전부 라틴 전용 — 한글 글리프 없음

## 수정한 버그

### 쿼리창·메모장에서 Enter/Shift+Enter가 줄바꿈되지 않음

`TMP_InputField.OnSubmit`이 `lineType`을 보지 않고 무조건 `DeactivateInputField()`를
호출한다. EventSystem이 Enter를 submit으로 잡아 이 핸들러를 먼저 부르므로 필드가
비활성화되고, 그 뒤 `OnUpdateSelected`가 `if (!isFocused) return;`에서 빠져나가
Return 이벤트가 큐에서 꺼내지지도 않는다. 결과적으로 줄바꿈은 되지 않고 캐럿만 사라졌다.
해당 필드들은 `m_OnSubmit`에 리스너가 없어 제출도 일어나지 않았다.

Ctrl+Enter 제출이 멀쩡했던 것은 그쪽이 Input System의 `"Enter Query"` 액션이라
이 경로와 무관했기 때문이다.

부차적으로 Shift+Enter는 `KeyPressed`에서 `'\v'`로 바뀌는데 `IsValidChar`의
`c < ' '` 검사에 걸려 `Append`까지 도달하지 못한다. 게임쪽
`QueryInputUtils.ValidateInput`의 `ILLEGAL_CHARS`에도 `'\r'`, `'\v'`가 들어 있다.

수정: 여러 줄 필드에서 `OnSubmit`을 건너뛰고, `'\r'`·`'\v'`를 `'\n'`으로 정규화한다.
한 줄짜리 입력 필드(로그인, 검색창)는 건드리지 않는다.

## 덧붙인 것

번역만으로는 해결되지 않아 플러그인 쪽에서 따로 손본 것들. 전부 설정에서 끌 수 있다.

| 기능 | 하는 일 |
|---|---|
| 말풍선 크기 다시 잡기 | 조수 말풍선은 **글자 수 × 15px**로 크기를 잡아 한글에서 잘렸다. TMP로 실제 너비를 재서 다시 잡는다 (`AssistantDialoguePatches`) |
| 원본/번역 전환 버튼 | 사진 단서 창과 설명서에 붙는다. 원본 그림을 눈으로 대조할 수 있다 (`ClueImagePatches`, `ManualPatches`) |
| HELP 커서 한글화 | 조수 위의 툴팁은 글자가 아니라 32×32 커서 텍스처다. 한글로 다시 그렸다 (`CursorPatches`) |
| broker.com 화면 손질 | 웹사이트가 없는 회사는 **`웹사이트` 라벨째** 감추고, 라벨을 값의 첫 줄 베이스라인에 맞춘다 (`BrokerPagePatches`) |
| 팝업 키로 닫기 | 알림·오류 팝업을 Esc나 Enter로 닫는다. 원래는 X 버튼뿐 (`PopupPatches`) |
| 타건음 | 글자를 칠 때마다 짧은 소리를 낸다 (`TypingSound`) |
| 장 미리보기 | 아직 못 간 장을 열어 번역을 확인한다 (`PreviewPatches`). 아래 참고 |

### 장 미리보기

`PreviewAllChapters = true`로 두면 조수에게 **`시간 여행.`**을 고를 때 나오는
사건 목록에 모든 장이 나온다. 아직 풀지 않은 사건의 화면과 단서를 열어 볼 수 있다.

`Save.GetMaxLevelUnlocked()`를 부풀리는 방식이라 **켜 둔 동안에는 진행이 저장되지 않는다.**
실수로 세이브를 망치지 않도록 처음 켤 때 `SQLGame.save`를 백업해 둔다.
번역 확인용이므로 평소에는 꺼 둘 것.

## 한글 폰트

OS에 설치된 폰트를 `AtlasPopulationMode.DynamicOS`로 참조해 TMP 폴백에 건다.
라틴 글자는 원래 폰트 모양을 유지하고 한글만 폴백에서 가져온다.
글리프를 필요할 때 OS에서 가져오므로 **폰트 파일을 동봉하지 않아 재배포 라이선스 문제가 없다.**

기본값은 동봉한 **Neo둥근모**(`FontFile = neodgm.ttf`)다. `FontFile`이 비어 있으면
OS에 설치된 `FontFamily` 폰트(기본 맑은 고딕)로 돌아간다. 굴림(`Gulim`)으로 바꾸면
게임의 Windows 95풍 UI와 잘 어울린다.

## 동봉 폰트

`dist/fonts/neodgm.ttf` — **Neo둥근모** (Eunbin Jeong / Dalgona), SIL Open Font License 1.1.
라이선스 원문은 같은 폴더의 `LICENSE.txt`에 있다. OFL은 원문 동봉을 요구하므로
패치를 배포할 때 이 파일을 함께 넣어야 한다. 예약 글꼴 이름이 지정되어 있으니
글꼴을 고쳐 쓸 경우 이름을 바꿔야 한다.

옛 윈도우의 각진 한글 느낌은 글꼴에 미리 그려 넣은 비트맵 글리프에서 나왔다.
요즘 렌더링은 외곽선을 부드럽게 그려내고 TMP는 SDF로 한 번 더 다듬으므로
같은 굴림 파일을 써도 그 느낌이 나지 않는다. 외곽선 자체가 계단 모양인
픽셀 글꼴을 쓰면 SDF를 통과해도 결이 살아남는다.

### 글꼴 바꾸기

`fonts/` 폴더에 `.ttf`/`.otf`를 넣고 설정의 `FontFile`에 파일 이름을 적으면 끝이다.
재빌드가 필요 없다.

권장 후보:

| 글꼴 | 느낌 | 라이선스 |
|---|---|---|
| Neo둥근모 (동봉) | 옛 윈도우의 각진 도트 | OFL 1.1 |
| 그리운 몽토리체 | 동글동글한 손글씨 | 모든 사용 범위 자유, 개작·수정·판매 금지 |
| 굴림 (OS 기본) | 2000년대 한국 윈도우 UI | 윈도우 동봉 글꼴이라 재배포 불가 |

그리운 몽토리체는 www.griun.co.kr/fonts/mongtori 에서 받는다.
다운로드가 자바스크립트로 동작해 자동으로 받아올 수 없으므로 직접 내려받아야 한다.
금지 항목이 개작·수정·판매 셋뿐이고 재배포는 포함되어 있지 않으므로,
원본 파일을 고치지 않고 무료 패치에 그대로 넣는 것은 허용 범위로 읽힌다.
동봉할 경우 출처와 라이선스 문구를 함께 적고 파일을 고치지 말 것.
확실히 하려면 contact@griun.co.kr 에 문의하면 된다.

## 타건음 바꾸기

원본을 `sounds/` 에 넣고 아래를 돌리면 `dist/sounds/` 로 손질된 음원이 나온다.
그것을 플러그인 폴더의 `sounds/` 에 넣으면 게임 내 소리 대신 쓴다.

```sh
python tools/build_sounds.py     # ffmpeg 필요
```

손질이 필요한 이유는 녹음 파일 앞에 무음이 붙어 있기 때문이다.
이 프로젝트의 원본은 0.15~0.23초였는데, 그대로 쓰면 키를 치고 그만큼 늦게 소리가 난다.
도구가 앞 무음을 떼고, 길이를 0.4초로 줄이고 끝을 서서히 줄이고,
무압축 WAV 모노로 바꾸고 파일 간 음량을 맞춘다.

손질 없이 원본을 바로 넣어도 읽기는 한다. `.mp3`, `.wav`, `.ogg`, `.aiff`를 지원하고
하위 폴더까지 훑는다. 여러 개면 칠 때마다 번갈아 나와 사람이 치는 느낌이 난다.

게임 자산에는 진짜 키보드 소리가 없다. 마우스, 펜, 버튼 계열뿐이라
직접 넣은 음원이 훨씬 낫다. 폴더를 비우면 게임 내 소리(`TypingClip`)로 돌아간다.

동봉해 배포할 경우 해당 음원의 이용 조건을 확인할 것.

## 번역 작업 흐름

### 글자

```sh
python tools/extract_text.py      # 게임에서 텍스트 추출 -> extracted/
python tools/make_templates.py    # 번역 템플릿 생성 -> translation/
#   translation/ui.json           : UI 문자열 (원문 -> 번역). 값을 채운다.
#   translation/dynamic.json      : 코드가 조립해 쓰는 문자열
#   translation/textassets/*.txt  : 대사·힌트. 구분자를 두고 텍스트만 고친다.
python tools/build_translation.py # dist/translation.json 으로 묶기
```

화면에 찍히는 문자열이 코드 안에 박혀 있는 것도 많다. 생김새로 짐작하면 테이블 이름까지
딸려 오므로, **호출 지점을 보고** 고른다 (`SetText`, `CreateQuestionAnswer`,
`GetHelpWrapper`, `Launch*Popup` 등).

```sh
python tools/extract_code_strings.py     # Scripts.dll 문자열 후보
python tools/extract_dialogue_strings.py # 호출 지점으로 거르기
python tools/filter_code_strings.py      # 실제로 번역할 것만 남기기
```

### 그림

사진 단서와 설명서는 텍스처라 글자를 바꿔 넣을 수 없다. **원본 그림에서 글자만 걷어내고
그 자리에 한글을 얹어** 새 PNG를 만든다. 그림을 다시 그리지는 않는다.

```sh
python tools/extract_images.py                 # 단서 그림 -> extracted/images/
python tools/extract_manual.py                 # 설명서 23쪽 -> extracted/images/manual/
python tools/measure_image.py <이름> [--box …]  # 글줄이 놓인 자리·색을 잰다
python tools/build_clue_images.py [이름 …]      # 사양대로 그려 dist/images/ 로
python tools/build_cursor.py                   # HELP 커서 그림
```

`extract_images.py`는 같은 이름의 스프라이트를 여럿 뽑아 놓는다(`brochure_1__2.png` 등).
그중 쓸 것을 골라 `extracted/images/clues/`에 정리해 두면 빌드가 거기서 읽는다.
설명서는 이름이 규칙적이라(`8-3`) `extract_manual.py`가 바로 제자리에 뽑는다.

편집 사양은 `translation/images/<이름>.json`에 둔다 (설명서는 `manual/` 아래).
이름 없이 돌리면 전부 다시 만든다.

| 키 | 하는 일 |
|---|---|
| `erase_fill` | 기본으로 덮을 색 |
| `erase_boxes` | 네모를 통째로 덮는다. `[x1,y1,x2,y2]` 또는 `{"box": […], "fill": [r,g,b]}` |
| `erase_colour_within` | 상자 안에서 **지정한 색에 가까운 화소만** 지운다. 글자가 기울었거나 그림과 얽혀 네모로 못 잡을 때 |
| `erase_ink_within` | 상자 안에 **통째로 들어가는 잉크 덩어리만** 지운다. 화살표·동그라미는 상자 밖으로 뻗으므로 살아남는다 |
| `texts` | 낱줄 글자. `at`, `align`(left/center/right), `valign`(top/middle), `size`, `font`, `weight`, `angle`, `color`, `line_gap` |
| `blocks` | 상자 안에 어절 단위로 흘려 넣는 문단. `box`, `size`, `font`, `color`, `line_spacing`, `indent` |
| `overlays` | 문단 **위에** 덧그리는 글자. 한 색으로 그려진 문단에서 키워드만 색을 바꿀 때 |

`font`는 `gulim`, `gulimche`, `dotum`, `dotumche`, `batang`, `neodgm`, `mongtori`,
`magic`(매직체), `pyunji`(편지체), `gungso`(궁서) 등을 이름으로 고른다.
없는 이름이면 굴림으로 떨어진다. `weight`는 굵은 서체가 없는 글꼴에 획을 덧그려
굵기를 흉내 낸다.

빌드는 **문장을 말없이 잃지 않는다.** 상자에 다 못 담으면
`N줄을 못 그렸다`, 넘치면 `상자를 Npx 넘쳤다`로 알려 준다. 이 두 줄이 뜨면
글을 줄이거나 상자를 넓혀야 한다.

```sh
python tools/build_clue_images.py 8-1 | grep -E "못 그렸|넘쳤"
```

#### 이름이 겹치는 그림

스프라이트 이름만으로는 구분되지 않는 경우가 있다. `victim`이라는 이름의 스프라이트가
사건마다 다른 그림(512×512 지구본, 650×563 샌드위치)이었다. 파일 이름을
`<이름>@<가로>x<세로>.png`로 두면 플러그인이 크기까지 맞춰 고른다.
크기를 붙인 것을 먼저 찾고, 없으면 이름만으로 찾는다.

#### 손대지 않은 그림

글자가 없는 그림(인물 사진, 증언 아이콘)과 `security_footage`는 원본 그대로 둔다.
`security_footage`의 벽 명패는 기울어진 데다 안쪽에 결이 있어, 네모로 덮으면 스티커를
붙인 꼴이 되고 잉크만 지우면 자국이 남았다. 그 안의 시각 정보는 원래 번역 대상도 아니다.

### 검사

번역을 넣은 뒤 돌린다.

```sh
python tools/check_data_collisions.py  # 조회 대상 값과 겹치는 번역 찾기 (아래 참고)
python tools/check_breaks.py           # 줄바꿈 표기가 온전한지
python tools/rewrap_hints.py           # 힌트의 줄 수를 원문에 맞추기
python tools/locate_text.py            # 번역한 문구가 게임 안 어느 쪽에 나오는지
python tools/mark_skipped.py           # 일부러 안 옮긴 것을 이유와 함께 적어 두기
```

`locate_text.py`는 TMP 컴포넌트에서 부모를 타고 올라가 주소처럼 생긴 프리팹 이름을
찾는다. 웹 화면은 프리팹 하나가 한 쪽이라 그 이름이 곧 주소다.
결과는 `extracted/text_locations.json`에 쪽별로 모인다.
번역을 눈으로 확인할 때 어디를 열어야 하는지 여기서 본다.

일부러 남긴 것은 `translation/ui_keep_original.json`과
`translation/code_strings_skipped.json`에 이유와 함께 적혀 있다.
다음에 볼 때 "빠뜨린 것"과 구별하기 위해서다.

### 빌드와 배포

```sh
dotnet build src/DDKoreanPatch/DDKoreanPatch.csproj -c Release
```

`<게임폴더>/BepInEx/plugins/DDKoreanPatch/` 에 아래를 넣는다.

```
DDKoreanPatch.dll
translation.json      <- dist/translation.json
images/               <- dist/images/*.png
fonts/                <- dist/fonts/ (neodgm.ttf, LICENSE.txt)
sounds/               <- dist/sounds/ (없으면 게임 내 소리를 쓴다)
```

그림과 폰트, 음원은 DLL이 읽기만 하므로 **바꿔 넣을 때 재빌드가 필요 없다.**

플러그인은 켜질 때 패치한 메서드 수를 로그에 남긴다.
`Plugin.cs`에서 `harmony.PatchAll(typeof(…))`을 클래스마다 **직접** 부르는 구조라,
새 패치 클래스를 만들고 등록을 잊으면 아무 일도 일어나지 않는다.
고친 게 반영되지 않으면 이 숫자부터 본다.

```
로드 완료. 메서드 18개 패치. EnterBehavior=Newline
```

### 배포판 만들기

```sh
python tools/make_release.py 1.0.1 --bump      # release/ 에 zip 두 개
python tools/make_release.py 1.0.1 --publish   # 태그를 밀고 Release까지
```

두 가지가 나온다.

| 파일 | 내용 | 누구에게 |
|---|---|---|
| `DDKoreanPatch-v<버전>.zip` | BepInEx + 패치 전부 | 처음 까는 사람. 게임 폴더에 풀면 끝 |
| `DDKoreanPatch-v<버전>-plugin-only.zip` | 패치만 | 이미 깐 사람. 번역만 새로 받을 때 |

BepInEx는 게임 폴더에 깔린 것을 그대로 담는다. 고치지 않은 공식 배포본이므로
LGPL-2.1에 따라 출처와 라이선스를 `packaging/NOTICE.txt`에 적어 함께 넣는다.

`--publish`는 `gh`(GitHub CLI)가 있어야 한다. 없으면 zip은 그대로 두고
직접 올리는 방법을 알려 준다. Release 본문은 `CHANGELOG.md`에서 그 버전 대목을
떼어 쓰므로, 버전을 올리기 전에 CHANGELOG부터 적는다.

**빌드를 CI에서 돌릴 수는 없다.** 컴파일에 게임의 `copOS_Data/Managed`
(UnityEngine.dll, Scripts.dll ...)가 필요한데 그것은 게임 원저작물이라 저장소에
올려 둘 수 없다. `.github/workflows/ci.yml`은 게임 없이 할 수 있는 것
(`tools/ci_check.py` — JSON과 그림 사양 검사)만 본다.

## 번역하면 안 되는 것

이 게임은 플레이어가 **SQL로 데이터를 조회**해 사건을 푼다.
조회 대상 데이터를 번역하면 쿼리가 통하지 않아 게임이 깨진다.

- `tools/extract_text.py`의 `KEEP_ORIGINAL`에 해당 TextAsset을 분류해 두었다
  (이름 목록, 영화 제목, 작물, 프로필 등 20개).
- **테이블 이름과 컬럼 이름도 원문을 유지해야 한다.** UI 문자열 중에도
  소문자 `exit`, `settings`, `search`, `arrest`, `clues`, `manual`, `messages`,
  `notepad`, `music player`, `web browser`처럼 실제 테이블명인 것이 섞여 있다.
  설명서 그림에 적힌 것도 화면의 아이콘 이름과 **한 글자도 다르면 안 된다.**
- 플레이어가 쿼리에 적어 넣는 값도 마찬가지다. 위키의 `Slimehead`, `Rare`,
  `Burning`, `Sword`는 설명글처럼 보이지만 `damage_log.character_damaged`,
  `inventory.weapon_name`의 값이다. `lsat.cs`는 입력을 `"Corrupted"`와 그대로 비교한다.

### 파일 단위로 가르면 놓친다

`guilds`, `broker-traders`, `profiles`는 한동안 통째로 `KEEP_ORIGINAL`에 있었다.
그런데 이 셋은 **칸마다 쓰임이 다르다.** 사람이 읽는 소개글 칸은 화면에 찍히기만 하고
테이블에 들어가지 않는다. 지금은 화면용 칸만 옮기고 나머지는 그대로 둔다.
자세한 내용은 `extract_text.py`의 주석에 적어 두었다.

### 자동 검사

같은 사고를 되풀이하지 않으려고 만들었다.

```sh
python tools/check_data_collisions.py
```

C# 문자열 리터럴을 전부 훑어, 번역한 `ui.json` 키가 그 안에 들어 있으면 알린다.
`$"Slimehead #{id}"` 같은 조립 문자열까지 잡는다. 사람이 확인한 안전한 낱말은
스크립트 안의 `REVIEWED`에 적어 둔다. 지금은 0건.

## 번역 어투

**[`translation/STYLE.md`](translation/STYLE.md)에 적어 두었다.** 화자에 따라 넷으로 가른다.

| 대상 | 어투 |
|---|---|
| 조수 | 해요체 |
| 시스템·오류 메시지 | 합니다체 |
| 등장인물·게시글·뉴스 | 반말 누아르 하드보일드 |
| 사용 설명서 | 합쇼체. 짧은 평서문, 현재형, `아십니까?` 같은 설의법 |

길이·줄바꿈 규칙과 원문으로 두는 것들도 같은 문서에 있다. 옮기기 전에 읽는다.

## 번역 제안 받기

이슈로 받는다. `.github/ISSUE_TEMPLATE/`에 양식을 두었다. 어디서 봤는지,
지금 번역, 제안을 나누어 받고, 번역하지 않는 것들(테이블·컬럼 이름, SQL 키워드,
고유명사, 쿼리에 적는 값)을 미리 알린다. 고치면 게임이 깨지는 제안을 받고
되돌리는 일을 줄이기 위해서다.

번역 파일 자체는 `translation/` 아래에 그대로 있으므로 PR로 받을 수도 있다.

### 표로 뽑아 보기

원문과 지금 번역을 나란히 놓은 CSV로 뽑을 수 있다. 아직 밖에 내놓을 만큼
정리된 것은 아니고, 손에서 훑어볼 때 쓴다.

```sh
python tools/export_sheet.py                     # release/translation-sheet.csv
python tools/import_sheet.py 받은표.csv --dry-run  # 무엇이 바뀔지만 본다
python tools/import_sheet.py 받은표.csv            # 제자리에 도로 넣는다
```

엑셀이 알아보도록 BOM을 붙여 내보낸다. 구글 시트에도 그대로 올라간다.

`열쇠` 칸이 그 글이 있던 자리를 가리킨다. 표에서 열쇠를 고치거나 행을 지우면
되돌려 넣지 못한다. 되돌릴 때는 `지금 번역` 칸이 파일의 현재 내용과 같은지
먼저 보고, 다르면 건너뛴다. 표를 뽑은 뒤에 이미 고친 자리를 덮어쓰지 않기 위해서다.

넣은 뒤에는 다시 묶어야 게임에 들어간다 (`build_translation.py`,
그림을 고쳤으면 `build_clue_images.py`).

## 번역 현황

| 갈래 | 상태 |
|---|---|
| UI 문자열 (`ui.json`) | 886개 중 752개. 남긴 134개는 테이블명 등 일부러 둔 것 |
| 코드 조립 문자열 (`dynamic.json`) | 214개 |
| TextAsset (대사·힌트·웹페이지) | 41개 |
| 사진 단서 그림 | 21장 (+ 글자 없는 그림은 원본 유지) |
| 사용 설명서 | **23쪽 전부** |
| 커서 | HELP 커서 1개 |

## 설정

`<게임폴더>/BepInEx/config/kr.spade.databasedetective.koreanpatch.cfg`

| 항목 | 기본값 | 설명 |
|---|---|---|
| **Input** | | |
| `EnterBehavior` | `Newline` | `Newline`=Enter·Shift+Enter 줄바꿈, 제출은 Ctrl+Enter / `Submit`=Enter 제출, Shift+Enter 줄바꿈 |
| `ClosePopupWithKey` | `true` | 팝업을 Esc·Enter로 닫기 |
| **Font** | | |
| `EnableKoreanFont` | `true` | 한글 폰트 폴백 주입 |
| `FontFile` | `neodgm.ttf` | 플러그인 `fonts/` 안의 폰트 파일. 있으면 `FontFamily`보다 먼저 쓴다 |
| `FontFamily` | `Malgun Gothic` | 한글 글리프를 가져올 OS 폰트 |
| `FontStyle` | `Regular` | 폰트 스타일 |
| `FontPointSize` | `64` | 폰트 샘플링 크기 |
| `FontAtlasPadding` | `4` | 글자 외곽 여백. 픽셀 글꼴은 작을수록 또렷하다 (보통 글꼴은 9) |
| `FontScale` | `0.95` | 폴백 글리프 크기 보정 |
| `FontBaselineOffset` | `0.09` | 폴백 글리프 세로 위치 보정 |
| `ModernHangulLineBreaking` | `true` | 한글을 어절 단위로 끊는다 |
| **Translation** | | |
| `EnableTranslation` | `true` | 번역 적용 |
| `ShrinkTextToFit` | `true` | 번역문이 넘칠 때만 글자를 조금 줄인다 |
| `ShrinkFloor` | `0.72` | 줄일 수 있는 하한 |
| `FitAssistantBubble` | `true` | 조수 말풍선 크기를 번역문 너비에 맞춰 다시 잡는다 |
| `EnableClueImageToggle` | `true` | 단서 창·설명서에 원본/번역 전환 버튼 |
| **Sound** | | |
| `EnableTypingSound` | `true` | 타건음 |
| `TypingVolume` | `0.22` | 타건음 크기 |
| `TypingClip` | `click down` | 쓸 소리 이름 (`sounds/` 폴더가 비었을 때) |
| **Preview** | | |
| `PreviewAllChapters` | `false` | 모든 장을 열어 번역 확인. **켜면 진행이 저장되지 않는다** |
| **Debug** | | |
| `VerboseInputLog` | `false` | 입력 진단 로그 |

## 제거

게임 폴더에서 아래만 지우면 원상복구된다. 원본 파일은 수정하지 않았다.

```
winhttp.dll  doorstop_config.ini  .doorstop_version  changelog.txt  BepInEx/
```

`PreviewAllChapters`를 켜 본 적이 있다면 백업해 둔 `SQLGame.save`도 확인할 것.

## 배포 시 유의

`translation/`과 `extracted/`에는 게임의 원문 텍스트가 그대로 들어 있다.
이 저장소를 공개하거나 패치를 배포할 때는 원문 대사를 그대로 싣지 않도록 주의할 것.
게임 본편 애셋은 어떤 형태로도 포함하지 않는다.

`dist/images/`의 PNG는 **원본 그림 위에 글자만 바꾼 것**이라 게임 애셋의 2차 저작물이다.
공개 저장소에 올리지 말고, 패치 배포물에만 넣는다.
