// dashboard.js — Chart.js charts for admin dashboard

document.addEventListener('DOMContentLoaded', () => {
  // ── Monthly Transactions Chart ──
  const ctxMonthly = document.getElementById('monthlyChart');
  if (ctxMonthly && typeof monthlyData !== 'undefined') {
    const labels = [...monthlyData].reverse().map(d => d.month || 'N/A');
    const values = [...monthlyData].reverse().map(d => d.total || 0);

    new Chart(ctxMonthly, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Volume (DNT)',
          data: values,
          backgroundColor: 'rgba(79,172,254,0.25)',
          borderColor: '#4facfe',
          borderWidth: 2,
          borderRadius: 8,
          borderSkipped: false,
          hoverBackgroundColor: 'rgba(79,172,254,0.45)',
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(15,24,48,0.95)',
            titleColor: '#4facfe',
            bodyColor: '#e2eaf4',
            borderColor: 'rgba(79,172,254,0.3)',
            borderWidth: 1,
            padding: 12,
            callbacks: {
              label: ctx => ' ' + ctx.parsed.y.toLocaleString('fr-TN', {minimumFractionDigits:2}) + ' DNT'
            }
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#8899b0', font: { size: 11 } }
          },
          y: {
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: {
              color: '#8899b0', font: { size: 11 },
              callback: v => (v/1000).toFixed(0) + 'K'
            }
          }
        }
      }
    });
  }

  // ── Account Status Doughnut ──
  const ctxStatus = document.getElementById('statusChart');
  if (ctxStatus && typeof accountStats !== 'undefined') {
    new Chart(ctxStatus, {
      type: 'doughnut',
      data: {
        labels: ['Actifs', 'Gelés', 'Fermés'],
        datasets: [{
          data: [accountStats.active, accountStats.frozen, accountStats.closed || 0],
          backgroundColor: [
            'rgba(0,201,167,0.8)',
            'rgba(79,172,254,0.8)',
            'rgba(255,71,87,0.8)'
          ],
          borderColor: ['#00c9a7','#4facfe','#ff4757'],
          borderWidth: 2,
          hoverOffset: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '70%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: '#8899b0', padding: 16, font: { size: 12 } }
          },
          tooltip: {
            backgroundColor: 'rgba(15,24,48,0.95)',
            titleColor: '#4facfe',
            bodyColor: '#e2eaf4',
            borderColor: 'rgba(79,172,254,0.3)',
            borderWidth: 1,
            padding: 12
          }
        }
      }
    });
  }

  // ── Customer Balance Line Chart ──
  const ctxBalance = document.getElementById('balanceChart');
  if (ctxBalance && typeof monthlyData !== 'undefined') {
    const labels = [...monthlyData].reverse().map(d => d.month || 'N/A');
    const counts = [...monthlyData].reverse().map(d => d.count || 0);

    new Chart(ctxBalance, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Transactions',
          data: counts,
          borderColor: '#00c9a7',
          backgroundColor: 'rgba(0,201,167,0.08)',
          borderWidth: 2.5,
          tension: 0.4,
          fill: true,
          pointBackgroundColor: '#00c9a7',
          pointRadius: 4,
          pointHoverRadius: 7
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(15,24,48,0.95)',
            titleColor: '#00c9a7',
            bodyColor: '#e2eaf4',
            borderColor: 'rgba(0,201,167,0.3)',
            borderWidth: 1, padding: 12
          }
        },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#8899b0', font: { size: 11 } } },
          y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#8899b0', font: { size: 11 } } }
        }
      }
    });
  }
});
