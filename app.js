const stocks = [
  {
    symbol: 'NVDA',
    company: 'NVIDIA',
    move: 8.4,
    sentiment: 'up',
    volume: '46.3M',
    price: '$126.80',
    description:
      'AI chip demand remains strong as hyperscalers accelerate infrastructure spending, lifting sentiment across semiconductor names.',
    catalysts: [
      'Data center AI spending continues to expand across cloud providers.',
      'Semiconductor demand remained elevated after strong enterprise GPU orders.',
      'Analysts cited improved margin outlook tied to new AI platform rollouts.'
    ],
    news: [
      {
        title: 'AI spending boom keeps chipmakers in focus',
        summary: 'Large cloud providers renewed capital expenditure guidance to support AI buildouts.'
      },
      {
        title: 'Analyst upgrades point to stronger GPU demand',
        summary: 'Street estimates moved higher after robust enterprise server demand and margin commentary.'
      }
    ]
  },
  {
    symbol: 'TSLA',
    company: 'Tesla',
    move: -6.8,
    sentiment: 'down',
    volume: '61.7M',
    price: '$182.55',
    description:
      'A sharp move lower followed concerns around vehicle margins and slower growth in key geographies, with traders citing weak delivery commentary.',
    catalysts: [
      'Investors reacted to renewed guidance concerns in Europe and China.',
      'Analysts flagged margin pressure from pricing strategies and operating costs.',
      'Market sentiment flipped after a weaker-than-expected delivery narrative.'
    ],
    news: [
      {
        title: 'Delivery outlook weighs on EV names',
        summary: 'Analysts revised expectations after signs of softer global demand and tighter margins.'
      },
      {
        title: 'Investors debate pricing versus volume tradeoff',
        summary: 'The market focused on whether lower prices can offset softer unit economics.'
      }
    ]
  },
  {
    symbol: 'AMD',
    company: 'Advanced Micro Devices',
    move: 6.1,
    sentiment: 'up',
    volume: '34.8M',
    price: '$169.21',
    description:
      'AMD outperformed as traders priced in stronger AI accelerator demand and continued execution in its data center portfolio.',
    catalysts: [
      'AI roadmap commentary reassured investors about future server demand.',
      'Competitive positioning in data center chips improved relative to peers.',
      'Market sentiment improved after better-than-expected product traction.'
    ],
    news: [
      {
        title: 'AI hardware momentum keeps pressure on rivals',
        summary: 'AMD gained attention as enterprise customers leaned into new accelerator deployments.'
      },
      {
        title: 'Investors rotate into chip names with strong AI exposure',
        summary: 'The sector continued to see breadth as market participants sought growth exposure.'
      }
    ]
  },
  {
    symbol: 'META',
    company: 'Meta Platforms',
    move: -4.7,
    sentiment: 'down',
    volume: '22.4M',
    price: '$487.13',
    description:
      'A pullback was tied to concerns around ad spending and rising infrastructure costs, even as AI investments remain a strategic priority.',
    catalysts: [
      'Advertising growth expectations were trimmed in some analyst notes.',
      'Infrastructure investment remained elevated, keeping margin watchlists active.',
      'The broader tech sector showed rotation into lower-beta growth names.'
    ],
    news: [
      {
        title: 'Ad spend questions dampen large-cap growth sentiment',
        summary: 'Investors worried that slowing digital ad growth could pressure near-term profitability.'
      },
      {
        title: 'AI capex story remains positive but costs are front and center',
        summary: 'Meta continues to invest heavily, though traders remain focused on execution and returns.'
      }
    ]
  },
  {
    symbol: 'AAPL',
    company: 'Apple',
    move: 3.2,
    sentiment: 'up',
    volume: '29.5M',
    price: '$216.72',
    description:
      'Apple gained ground on optimism around services growth and improving demand in premium devices despite a mixed broader tech backdrop.',
    catalysts: [
      'Services revenue remained resilient and supported valuation multiples.',
      'Investors noted strength in premium device demand and ecosystem monetization.',
      'The stock benefited from defensive quality demand within large-cap tech.'
    ],
    news: [
      {
        title: 'Services strength balances hardware worries',
        summary: 'Apple continued to attract attention from investors seeking durable high-margin revenue streams.'
      },
      {
        title: 'Large-cap tech rotation boosts premium quality names',
        summary: 'Defensive equity demand supported broader large-cap leadership.'
      }
    ]
  },
  {
    symbol: 'PLTR',
    company: 'Palantir',
    move: 9.2,
    sentiment: 'up',
    volume: '58.1M',
    price: '$32.86',
    description:
      'Palantir saw a major move higher as traders continued to reward AI and enterprise software momentum, with attention on new contract wins.',
    catalysts: [
      'New enterprise AI contracts renewed excitement around revenue growth.',
      'The software pipeline remained a focal point for growth investors.',
      'Alphas remain constructive on operational leverage and AI monetization.'
    ],
    news: [
      {
        title: 'AI enterprise demand keeps software growth names elevated',
        summary: 'Large enterprise accounts continued to drive a strong pipeline and encouraging sentiment.'
      },
      {
        title: 'Contract wins support broader long-duration growth narrative',
        summary: 'Analysts continued to favor names with visible AI monetization opportunities.'
      }
    ]
  }
];

const gainersList = document.getElementById('gainersList');
const losersList = document.getElementById('losersList');
const detailPanel = document.getElementById('stockDetail');
const catalystList = document.getElementById('catalystList');
const moveFilter = document.getElementById('moveFilter');
const symbolInput = document.getElementById('symbolInput');
const searchBtn = document.getElementById('searchBtn');

function formatMove(move) {
  return `${move > 0 ? '+' : ''}${move.toFixed(1)}%`;
}

function renderStockList(items, container) {
  container.innerHTML = '';

  items.forEach((stock) => {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'stock-item';
    item.innerHTML = `
      <div class="stock-symbol">
        <strong>${stock.symbol}</strong>
        <span>${stock.company}</span>
      </div>
      <div class="stock-change ${stock.sentiment === 'up' ? 'positive' : 'negative'}">${formatMove(stock.move)}</div>
    `;
    item.addEventListener('click', () => renderDetail(stock));
    container.appendChild(item);
  });
}

function renderDetail(stock) {
  detailPanel.innerHTML = `
    <div class="detail-header">
      <h3>${stock.symbol}</h3>
      <span class="badge ${stock.sentiment === 'up' ? 'positive' : 'negative'}">${formatMove(stock.move)}</span>
    </div>
    <div class="detail-meta">
      <span>${stock.company}</span>
      <span>${stock.price}</span>
      <span>Volume: ${stock.volume}</span>
    </div>
    <p class="summary">${stock.description}</p>
    <div class="news-list">
      ${stock.news
        .map(
          (item) => `
            <div class="news-item">
              <h4>${item.title}</h4>
              <p>${item.summary}</p>
            </div>
          `
        )
        .join('')}
    </div>
  `;

  catalystList.innerHTML = stock.catalysts
    .map((item) => `<li>${item}</li>`)
    .join('');
}

function applyFilter() {
  const filter = moveFilter.value;
  const filtered = filter === 'all'
    ? stocks
    : stocks.filter((stock) => stock.sentiment === filter);

  const gainers = filtered.filter((stock) => stock.sentiment === 'up').sort((a, b) => b.move - a.move);
  const losers = filtered.filter((stock) => stock.sentiment === 'down').sort((a, b) => a.move - b.move);

  renderStockList(gainers, gainersList);
  renderStockList(losers, losersList);

  const initial = filtered[0] || stocks[0];
  renderDetail(initial);
}

function analyzeSymbol() {
  const value = symbolInput.value.trim().toUpperCase();
  if (!value) {
    applyFilter();
    return;
  }

  const match = stocks.find((stock) => stock.symbol === value);
  if (match) {
    renderDetail(match);
    return;
  }

  const fallback = stocks[0];
  renderDetail(fallback);
  alert(`No stock matching ${value} was found. Showing the strongest market mover instead.`);
}

moveFilter.addEventListener('change', applyFilter);
searchBtn.addEventListener('click', analyzeSymbol);
symbolInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    analyzeSymbol();
  }
});

applyFilter();
