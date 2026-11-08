// 팀 예매·결제 API가 준비되면 startPayment를 연결한다.
// 입력: { showId, performanceId, performanceSeatId }. 표시 가격과 예시 위치는 보내지 않는다.
// 팀 서버에서 로그인 토큰을 검증하고 주문번호·금액을 확정한 뒤 토스페이먼츠 결제창을 연다.
// 인증 성공 URL에서 돌아온 paymentKey/orderId/amount는 서버에서 주문 정보와 대조한 뒤 승인한다.
// 승인 결과와 예매 확정은 결제 복귀 화면에서 처리한다. 시크릿 키는 서버에서만 사용한다.
const bookingGateway = { startPayment: null };
