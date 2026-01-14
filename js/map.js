/**
 * Poutine Index - Interactive Map
 * Uses Leaflet.js to display poutine prices across Canadian cities
 */

(function() {
  'use strict';

  // Configuration
  const CONFIG = {
    // Map center (roughly center of Canada)
    center: [60, -95],
    zoom: 4,
    minZoom: 3,
    maxZoom: 12,

    // Price range for color gradient (CAD for regular size)
    priceMin: 8,
    priceMax: 16,

    // Colors (purple to orange - colorblind friendly)
    colorCheap: '#7b2d8e',
    colorMid: '#c44536',
    colorExpensive: '#f77f00',

    // Data file path
    dataUrl: 'data/cities_final.json'
  };

  // Province/territory full names
  const PROVINCE_NAMES = {
    'AB': 'Alberta',
    'BC': 'British Columbia',
    'MB': 'Manitoba',
    'NB': 'New Brunswick',
    'NL': 'Newfoundland and Labrador',
    'NS': 'Nova Scotia',
    'NT': 'Northwest Territories',
    'NU': 'Nunavut',
    'ON': 'Ontario',
    'PE': 'Prince Edward Island',
    'QC': 'Quebec',
    'SK': 'Saskatchewan',
    'YT': 'Yukon'
  };

  let map;
  let markersLayer;

  /**
   * Initialize the map
   */
  function initMap() {
    // Create map instance
    map = L.map('map', {
      center: CONFIG.center,
      zoom: CONFIG.zoom,
      minZoom: CONFIG.minZoom,
      maxZoom: CONFIG.maxZoom,
      scrollWheelZoom: true
    });

    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // Create markers layer group
    markersLayer = L.layerGroup().addTo(map);

    // Add legend
    addLegend();

    // Load and display data
    loadData();
  }

  /**
   * Load city data from JSON file
   */
  async function loadData() {
    try {
      const response = await fetch(CONFIG.dataUrl);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();

      // Update last updated date
      updateLastUpdated(data.last_updated);

      // Add markers for each city
      data.cities.forEach(city => addCityMarker(city));

    } catch (error) {
      console.error('Error loading data:', error);
      showError('Failed to load poutine price data. Please try again later.');
    }
  }

  /**
   * Calculate color based on price
   * Uses interpolation between cheap (purple), mid (red), and expensive (orange)
   */
  function getPriceColor(price) {
    if (price === null || price === undefined) {
      return '#999999'; // Gray for N/A
    }

    // Normalize price to 0-1 range
    const normalized = Math.max(0, Math.min(1,
      (price - CONFIG.priceMin) / (CONFIG.priceMax - CONFIG.priceMin)
    ));

    // Interpolate between colors
    if (normalized <= 0.5) {
      return interpolateColor(CONFIG.colorCheap, CONFIG.colorMid, normalized * 2);
    } else {
      return interpolateColor(CONFIG.colorMid, CONFIG.colorExpensive, (normalized - 0.5) * 2);
    }
  }

  /**
   * Interpolate between two hex colors
   */
  function interpolateColor(color1, color2, factor) {
    const c1 = hexToRgb(color1);
    const c2 = hexToRgb(color2);

    const r = Math.round(c1.r + (c2.r - c1.r) * factor);
    const g = Math.round(c1.g + (c2.g - c1.g) * factor);
    const b = Math.round(c1.b + (c2.b - c1.b) * factor);

    return rgbToHex(r, g, b);
  }

  /**
   * Convert hex color to RGB object
   */
  function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : null;
  }

  /**
   * Convert RGB values to hex color
   */
  function rgbToHex(r, g, b) {
    return '#' + [r, g, b].map(x => {
      const hex = x.toString(16);
      return hex.length === 1 ? '0' + hex : hex;
    }).join('');
  }

  /**
   * Format price for display
   */
  function formatPrice(price) {
    if (price === null || price === undefined) {
      return 'N/A';
    }
    return '$' + price.toFixed(2);
  }

  /**
   * Format affordability index (minutes of work)
   */
  function formatAffordability(minutes) {
    if (minutes === null || minutes === undefined) {
      return 'N/A';
    }
    const rounded = Math.round(minutes);
    return `${rounded} min`;
  }

  /**
   * Create popup content for a city
   */
  function createPopupContent(city) {
    const provinceName = PROVINCE_NAMES[city.province] || city.province;

    const smallPrice = city.prices.small ? formatPrice(city.prices.small.mean) : 'N/A';
    const regularPrice = city.prices.regular ? formatPrice(city.prices.regular.mean) : 'N/A';
    const largePrice = city.prices.large ? formatPrice(city.prices.large.mean) : 'N/A';

    return `
      <div class="popup-content">
        <div class="popup-title">${city.name}</div>
        <div class="popup-province">${provinceName}</div>

        <div class="popup-prices">
          <table>
            <tr>
              <th>Small</th>
              <th>Regular</th>
              <th>Large</th>
            </tr>
            <tr>
              <td>${smallPrice}</td>
              <td>${regularPrice}</td>
              <td>${largePrice}</td>
            </tr>
          </table>
        </div>

        <div class="popup-affordability">
          <strong>${formatAffordability(city.affordability_index)}</strong> of min. wage work
        </div>

        <div class="popup-meta">
          ${city.sample_size} restaurant${city.sample_size !== 1 ? 's' : ''} sampled<br>
          Min. wage: $${city.minimum_wage.toFixed(2)}/hr
        </div>
      </div>
    `;
  }

  /**
   * Add a marker for a city
   */
  function addCityMarker(city) {
    const regularPrice = city.prices.regular ? city.prices.regular.mean : null;
    const color = getPriceColor(regularPrice);

    // Create circle marker
    const marker = L.circleMarker([city.lat, city.lon], {
      radius: getMarkerRadius(city.sample_size),
      fillColor: color,
      color: '#ffffff',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.85
    });

    // Add popup
    marker.bindPopup(createPopupContent(city), {
      maxWidth: 280,
      className: 'poutine-popup'
    });

    // Add tooltip for quick hover info
    marker.bindTooltip(city.name, {
      permanent: false,
      direction: 'top',
      offset: [0, -10]
    });

    // Add to markers layer
    marker.addTo(markersLayer);
  }

  /**
   * Calculate marker radius based on sample size
   */
  function getMarkerRadius(sampleSize) {
    // Base radius of 8, scales up slightly with more data
    return Math.min(8 + Math.sqrt(sampleSize) * 1.5, 16);
  }

  /**
   * Add legend control to map
   */
  function addLegend() {
    const legend = L.control({ position: 'bottomright' });

    legend.onAdd = function() {
      const div = L.DomUtil.create('div', 'leaflet-legend');

      div.innerHTML = `
        <h4>Average Price (Regular)</h4>
        <div class="gradient-bar"></div>
        <div class="labels">
          <span>$${CONFIG.priceMin}</span>
          <span>$${CONFIG.priceMax}+</span>
        </div>
      `;

      return div;
    };

    legend.addTo(map);
  }

  /**
   * Update the last updated date in the footer
   */
  function updateLastUpdated(dateString) {
    const element = document.getElementById('last-updated');
    if (element && dateString) {
      const date = new Date(dateString);
      const formatted = date.toLocaleDateString('en-CA', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
      element.textContent = `Last updated: ${formatted}`;
    }
  }

  /**
   * Show error message to user
   */
  function showError(message) {
    const mapContainer = document.getElementById('map');
    if (mapContainer) {
      const errorDiv = document.createElement('div');
      errorDiv.style.cssText = 'position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:#fff;padding:20px;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,0.2);text-align:center;z-index:1000;';
      errorDiv.innerHTML = `<p style="color:#c44536;margin:0;">${message}</p>`;
      mapContainer.appendChild(errorDiv);
    }
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMap);
  } else {
    initMap();
  }

})();
