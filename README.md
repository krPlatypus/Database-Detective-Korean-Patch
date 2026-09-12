# Database Detective 한글패치

Steam 게임 *Database Detective* (HsuCorp)의 한글패치 및 입력 버그 수정.
BepInEx 플러그인으로 동작하며 **게임 원본 파일은 수정하지 않는다.**

## 구성

| 경로 | 내용 |
|---|---|
| `src/DDKoreanPatch/` | BepInEx 플러그인 (C#) |
| `tools/` | 애셋 분석·텍스트 추출 스크립트 (Python) |
| `translation/` | 번역 작업 파일 (사람이 편집) |
| `dist/` | 플러그인이 읽는 번역 번들 |
| `extracted/` | 추출 원본 (git 제외) |
| `decompiled/` | 디컴파일 결과 (git 제외) |

## 게임 환경

- Unity **6000.5.5f1**, 스크립팅 백엔드 **Mono**
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

## 한글 폰트

OS에 설치된 폰트를 `AtlasPopulationMode.DynamicOS`로 참조해 TMP 폴백에 건다.
라틴 글자는 원래 폰트 모양을 유지하고 한글만 폴백에서 가져온다.
글리프를 필요할 때 OS에서 가져오므로 **폰트 파일을 동봉하지 않아 재배포 라이선스 문제가 없다.**

기본값은 맑은 고딕. 설정에서 굴림(`Gulim`)으로 바꾸면 게임의 Windows 95풍 UI와 더 잘 어울린다.

## 동봉 폰트

`dist/fonts/neodgm.ttf` — **Neo둥근모** (Eunbin Jeong / Dalgona), SIL Open Font License 1.1.
라이선스 원문은 같은 폴더의 `LICENSE.txt`에 있다. OFL은 원문 동봉을 요구하므로
패치를 배포할 때 이 파일을 함께 넣어야 한다. 예약 글꼴 이름이 지정되어 있으니
글꼴을 고쳐 쓸 경우 이름을 바꿔야 한다.

옛 윈도우의 각진 한글 느낌은 글꼴에 미리 그려 넣은 비트맵 글리프에서 나왔다.
요즘 렌더링은 외곽선을 부드럽게 그려내고 TMP는 SDF로 한 번 더 다듬으므로
같은 굴림 파일을 써도 그 느낌이 나지 않는다. 외곽선 자체가 계단 모양인
픽셀 글꼴을 쓰면 SDF를 통과해도 결이 살아남는다.

`FontFile`을 비우면 OS에 설치된 `FontFamily` 글꼴(기본 굴림)을 쓴다.

## 번역 작업 흐름

```sh
python tools/extract_text.py      # 게임에서 텍스트 추출 -> extracted/
python tools/make_templates.py    # 번역 템플릿 생성 -> translation/
#   translation/ui.json           : UI 문자열 (원문 -> 번역). 값을 채운다.
#   translation/textassets/*.txt  : 대사·힌트. 구분자를 두고 텍스트만 고친다.
python tools/build_translation.py # dist/translation.json 으로 묶기
```

빌드와 배포:

```sh
dotnet build src/DDKoreanPatch/DDKoreanPatch.csproj -c Release
# DDKoreanPatch.dll 과 translation.json 을
# <게임폴더>/BepInEx/plugins/DDKoreanPatch/ 에 복사
```

### 번역하면 안 되는 것

이 게임은 플레이어가 **SQL로 데이터를 조회**해 사건을 푼다.
조회 대상 데이터를 번역하면 쿼리가 통하지 않아 게임이 깨진다.

- `tools/extract_text.py`의 `KEEP_ORIGINAL`에 해당 TextAsset을 분류해 두었다
  (이름 목록, 영화 제목, 작물, 프로필 등 22개).
- **테이블 이름과 컬럼 이름도 원문을 유지해야 한다.** UI 문자열 중에도
  소문자 `exit`, `settings`처럼 실제 테이블명인 것이 섞여 있으니 주의.

## 설정

`<게임폴더>/BepInEx/config/kr.spade.databasedetective.koreanpatch.cfg`

| 항목 | 기본값 | 설명 |
|---|---|---|
| `EnterBehavior` | `Newline` | `Newline`=Enter·Shift+Enter 줄바꿈, 제출은 Ctrl+Enter / `Submit`=Enter 제출, Shift+Enter 줄바꿈 |
| `EnableKoreanFont` | `true` | 한글 폰트 폴백 주입 |
| `FontFamily` | `Malgun Gothic` | 한글 글리프를 가져올 OS 폰트 |
| `EnableTranslation` | `true` | 번역 적용 |
| `VerboseInputLog` | `false` | 입력 진단 로그 |

## 제거

게임 폴더에서 아래만 지우면 원상복구된다. 원본 파일은 수정하지 않았다.

```
winhttp.dll  doorstop_config.ini  .doorstop_version  changelog.txt  BepInEx/
```

## 배포 시 유의

`translation/`과 `extracted/`에는 게임의 원문 텍스트가 그대로 들어 있다.
이 저장소를 공개하거나 패치를 배포할 때는 원문 대사를 그대로 싣지 않도록 주의할 것.
게임 본편 애셋은 어떤 형태로도 포함하지 않는다.
