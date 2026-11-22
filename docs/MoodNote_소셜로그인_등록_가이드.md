# MoodNote 소셜 로그인 켜는 법 (카카오 · 네이버 · 구글)

코드는 이미 들어 있어요. 아래를 하면 버튼이 켜져요. **키(Client ID/Secret)는 서버의 `.env` 에만 적고, 채팅·깃·캡처에는 절대 올리지 않아요.**
키를 넣지 않은 업체 버튼은 "준비 중이에요"라고 보여서, 하나씩 켜도 괜찮아요. 추천 순서는 카카오 → 구글 → 네이버예요.

## 0. 먼저: 코드 올리고 DB 표 추가하기 (한 번만)

1. Mac 터미널에서 커밋하고 push 해요.
2. 서버(Lightsail 터미널)에서:
   ```
   bash ~/MoodNote/software/deploy/setup_server.sh update
   sudo mysql moodnote < ~/MoodNote/software/backend/migrate_v1_6.sql
   ```
   두 번째 줄이 `user_identities` 표를 만들어요. (두 번 해도 안전해요)
3. 이 단계 뒤에 앱이 평소처럼 열리면 성공이에요. 소셜 키가 아직 없으니 세 버튼은 "준비 중"으로 보여요.

## 1. 모든 업체에 똑같이 쓰는 값

| 이름 | 값 |
|---|---|
| 서비스 주소 | `https://52-64-236-218.sslip.io` |
| 카카오 Redirect URI | `https://52-64-236-218.sslip.io/api/auth/kakao/callback` |
| 네이버 Callback URL | `https://52-64-236-218.sslip.io/api/auth/naver/callback` |
| 구글 승인된 리디렉션 URI | `https://52-64-236-218.sslip.io/api/auth/google/callback` |

주소는 **한 글자도 다르면 안 돼요.** (끝의 `/`, http/https, 대소문자까지) 틀리면 업체 화면에서 `redirect_uri_mismatch` 같은 오류가 나요.

## 2. 카카오

1. https://developers.kakao.com → 로그인 → **내 애플리케이션 → 애플리케이션 추가하기** (앱 이름 MoodNote).
2. **앱 키**에서 **REST API 키**를 복사해 둬요 → `KAKAO_CLIENT_ID`.
3. **제품 설정 → 카카오 로그인**: 활성화 **ON**, **Redirect URI** 에 위 카카오 주소를 등록해요.
4. **동의 항목**은 아무것도 필수로 하지 않아도 돼요. (우리는 사용자 번호만 써요. 이메일은 비즈 앱이 필요하니 건드리지 않아요.)
5. **보안 → Client Secret** 이 "사용함"이면 코드를 복사해서 `KAKAO_CLIENT_SECRET` 에 넣어요. 꺼져 있으면 비워 둬요.

## 3. 구글

1. https://console.cloud.google.com → 프로젝트 만들기(이름 MoodNote).
2. **API 및 서비스 → OAuth 동의 화면**(또는 Google Auth Platform): 사용자 유형 **외부**, 앱 이름 MoodNote, 이메일 칸은 본인 주소. **범위(scope)는 추가하지 않아요.** (기본 `openid` 만 써요)
3. 게시 상태는 **테스트**로 두고, **테스트 사용자**에 로그인해 볼 구글 계정(본인, 친구)을 넣어요. 테스트 상태에서는 이 목록의 사람만 로그인할 수 있어요.
4. **사용자 인증 정보 → 사용자 인증 정보 만들기 → OAuth 클라이언트 ID** → 유형 **웹 애플리케이션** → **승인된 리디렉션 URI** 에 위 구글 주소 등록.
5. 만들어지면 나오는 **클라이언트 ID** → `GOOGLE_CLIENT_ID`, **클라이언트 보안 비밀** → `GOOGLE_CLIENT_SECRET`.

모두에게 공개하려면 동의 화면을 "프로덕션"으로 올려야 하고, 이때 **내가 소유한 도메인**이 필요할 가능성이 커요. (`sslip.io` 는 내 것이 아니에요.) 발표·시연은 테스트 사용자만으로 충분해요.

## 4. 네이버

1. https://developers.naver.com/apps → **애플리케이션 등록**.
2. **사용 API**: 네이버 로그인. **제공 정보**는 선택지에서 최소한으로 골라요. (우리는 사용자 번호만 쓰고 저장하지 않아요.)
3. **서비스 URL** `https://52-64-236-218.sslip.io`, **Callback URL** 위 네이버 주소.
4. 등록하면 **Client ID**, **Client Secret** 이 나와요 → `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`.
5. 개발 중 상태에서는 **멤버 관리**에 등록한 네이버 아이디만 로그인돼요. 다른 사람이 쓰게 하려면 네이버에 **검수 요청**을 해야 해요.

## 5. 서버 `.env` 에 넣기

서버에서 `nano ~/MoodNote/software/backend/.env` 를 열고 아래 줄을 추가/채워요. (`=` 앞뒤에 띄어쓰기·따옴표 없이)

```
PUBLIC_BASE_URL=https://52-64-236-218.sslip.io
KAKAO_CLIENT_ID=...
KAKAO_CLIENT_SECRET=...
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

저장(Ctrl+O, Enter) → 나가기(Ctrl+X) → 다시 시작해요:

```
sudo systemctl restart moodnote
```

`.env` 는 시작할 때만 읽어서, 바꾼 뒤에는 꼭 restart 가 필요해요.
`PUBLIC_BASE_URL` 과 `*_CLIENT_ID` 가 모두 있어야 켜지고, 네이버·구글은 `*_CLIENT_SECRET` 도 있어야 켜져요. 카카오는 Secret 없이도 돼요.

## 6. 시험해 보기

1. 앱 로그인 화면에서 켠 업체 버튼을 눌러요 → 업체 로그인/동의 화면 → 돌아오면 **동의 화면**이 나와요. (새 사용자라서요)
2. 설정에서 닉네임을 바꿔요. 처음 닉네임은 "새로운 친구"예요. (이름·이메일은 받아 오지 않아요)
3. 같은 계정으로 다시 로그인하면 같은 일기장이 나와요.
4. 설정 > 회원 탈퇴: 소셜 계정은 비밀번호가 없어서 **"탈퇴합니다"** 를 입력해요.

## 문제가 생기면

| 증상 | 확인할 것 |
|---|---|
| 업체 화면에서 redirect_uri 오류 | 업체에 등록한 주소와 위 표가 한 글자라도 다른지 |
| 돌아왔는데 "로그인 서비스와 연결하지 못했어요" | 키/Secret 오타, `.env` 수정 후 restart 했는지. `sudo journalctl -u moodnote -n 50` 에 업체가 보낸 오류 내용이 남아요 |
| 버튼이 계속 "준비 중" | `.env` 의 `PUBLIC_BASE_URL` 과 해당 업체 값, restart 여부 |
| 네이버/구글에서 "접근 불가" | 멤버(네이버) 또는 테스트 사용자(구글)로 등록한 계정인지 |

## 지금 정해진 동작 (참고)

- 저장하는 것은 업체 이름과 업체 안의 사용자 번호뿐이에요. 이메일·이름·사진은 저장하지 않아요.
- 이메일이 같아도 다른 로그인 방법의 계정과 **자동으로 합치지 않아요**. (남의 계정을 가로채는 길이 될 수 있어서요) 카카오로 만든 계정과 구글로 만든 계정은 서로 다른 계정이에요.
- 업체 버튼 아이콘은 공식 색을 따라 그린 임시 모양이에요. 공개하기 전에 각 업체 개발자 사이트의 공식 버튼 이미지/가이드로 바꿔야 해요.
- 앞으로 할 수 있는 것: 설정에서 "다른 로그인 방법 연결하기".
