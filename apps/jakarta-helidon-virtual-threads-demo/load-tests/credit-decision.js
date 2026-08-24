import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    steady_load: {
      executor: 'constant-vus',
      vus: Number(__ENV.VUS || 100),
      duration: __ENV.DURATION || '2m'
    }
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500']
  }
};

const baseUrl = __ENV.BASE_URL || 'http://localhost:8080';

export default function () {
  const id = Math.floor(Math.random() * 100000);
  const payload = JSON.stringify({
    customerId: `C${id}`,
    requestedAmount: 10000 + Math.floor(Math.random() * 90000),
    termMonths: [24, 36, 48, 60][Math.floor(Math.random() * 4)],
    annualIncome: 65000 + Math.floor(Math.random() * 125000),
    monthlyDebt: 500 + Math.floor(Math.random() * 4500),
    creditScore: 610 + Math.floor(Math.random() * 230)
  });

  const response = http.post(`${baseUrl}/credit-decisions`, payload, {
    headers: { 'content-type': 'application/json' }
  });

  check(response, {
    'status is 200': (r) => r.status === 200,
    'has decision id': (r) => r.status === 200 && Boolean(r.json('decisionId'))
  });

  sleep(Number(__ENV.SLEEP || 0.1));
}
