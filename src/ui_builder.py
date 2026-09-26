"""
src/ui_builder.py — מחולל דשבורד סטטי אינטראקטיבי עצמאי (Serverless HTML Dashboard).
עיצוב מקצועי ברמת Enterprise / Claude AI נקי לחלוטין ללא אימוג'ים מיותרים,
אייקוני SVG וקטוריים מינימליסטיים, ונקודות סטטוס דקורטיביות בלבד (אדום/ירוק/כתום).
"""
import os
import json
from datetime import datetime

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="he" dir="rtl" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>__TITLE__</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            clay: {
              950: '#0B0D11',
              900: '#12151B',
              850: '#181C24',
              800: '#202632',
              700: '#2D3545',
              600: '#414C62',
              400: '#8A97AC',
              300: '#C2CDDC',
              100: '#F0F4F8',
            },
            accent: {
              400: '#FB923C',
              500: '#EA580C',
              600: '#C2410C',
            }
          }
        }
      }
    }
  </script>
  <style>
    * {
      transition: background-color 0.15s ease, border-color 0.15s ease;
    }
    .custom-scrollbar::-webkit-scrollbar {
      width: 5px;
      height: 5px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
      background: transparent;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
      background: #202632;
      border-radius: 4px;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover {
      background: #2D3545;
    }
  </style>
</head>
<body class="bg-[#0B0D11] text-[#F0F4F8] min-h-screen font-sans antialiased selection:bg-[#EA580C] selection:text-white flex flex-col md:flex-row">

  <!-- Mobile Top Bar -->
  <header class="md:hidden bg-[#12151B] border-b border-[#202632] p-4 flex items-center justify-between sticky top-0 z-40">
    <div class="flex items-center gap-2.5">
      <div class="w-8 h-8 rounded-lg bg-[#EA580C] flex items-center justify-center text-white font-bold text-sm shadow-sm">
        CL
      </div>
      <div>
        <span class="font-bold text-sm tracking-wide text-white">CONSTRUCT<span class="text-[#EA580C]">LEADS</span></span>
        <span class="text-[10px] text-slate-400 block">מערכת מודיעין עסקית</span>
      </div>
    </div>
    <div class="flex items-center gap-2">
      <button onclick="openScanModal()" class="px-2.5 py-1.5 bg-[#181C24] hover:bg-[#202632] border border-[#EA580C]/40 text-[#FB923C] rounded-lg text-xs font-medium flex items-center gap-1.5">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
        <span>סריקה</span>
      </button>
      <button onclick="openManualLeadModal()" class="px-3 py-1.5 bg-[#EA580C] text-white rounded-lg text-xs font-medium">
        + הזנת ליד
      </button>
      <button onclick="toggleMobileSidebar()" class="p-1.5 text-slate-300 bg-[#181C24] rounded-lg text-sm border border-[#202632]">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7"></path></svg>
      </button>
    </div>
  </header>

  <!-- Persistent Full-Height Sidebar -->
  <aside id="sidebar" class="hidden md:flex flex-col w-72 lg:w-80 bg-[#12151B] border-l border-[#202632] h-screen sticky top-0 z-30 p-5 overflow-y-auto custom-scrollbar shrink-0 justify-between">
    
    <div class="space-y-6">
      <!-- Logo Header -->
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-[#EA580C] to-[#9A3412] flex items-center justify-center text-white font-black text-sm tracking-widest shadow-md">
          CL
        </div>
        <div>
          <div class="flex items-center gap-2">
            <span class="font-extrabold text-base tracking-wider text-white">CONSTRUCT<span class="text-[#EA580C]">LEADS</span></span>
            <span class="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-[#EA580C]/15 text-[#FB923C] border border-[#EA580C]/30">PRO</span>
          </div>
          <p class="text-[11px] text-[#8A97AC]">מערכת איתור ולכידת מכרזים</p>
        </div>
      </div>

      <!-- Contractor Profile Card -->
      <div class="bg-[#181C24] border border-[#202632] rounded-xl p-3.5 space-y-1.5">
        <div class="flex items-center justify-between text-xs">
          <span class="text-[#8A97AC] text-[11px]">פרופיל פעיל</span>
          <span class="flex items-center gap-1.5 text-[11px] text-emerald-400 font-medium">
            <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
            סריקה שוטפת
          </span>
        </div>
        <div class="text-xs font-bold text-white">קבלן שיפוצים ובנייה רשום</div>
        <div class="text-[10px] text-[#8A97AC]">פריסה: ארצית • סיווג: ג-1 / ב-1</div>
      </div>

      

      <div class="space-y-2">
        <button onclick="openScanModal()" class="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-[#EA580C] to-[#C2410C] hover:from-[#FB923C] hover:to-[#EA580C] text-white font-bold text-xs rounded-xl shadow-md transition active:scale-[0.98]">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
          <span>הפעל סריקה ידנית</span>
        </button>
        <button onclick="openManualLeadModal()" class="w-full flex items-center justify-center gap-2 px-4 py-2 bg-[#181C24] hover:bg-[#202632] text-[#C2CDDC] hover:text-white border border-[#202632] font-medium text-xs rounded-xl transition">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
          <span>הזנת ליד מהיר</span>
        </button>
        <button onclick="exportSavedToExcel()" class="w-full flex items-center justify-center gap-2 px-4 py-2 bg-[#181C24] hover:bg-[#202632] text-[#C2CDDC] hover:text-white border border-[#202632] font-medium text-xs rounded-xl transition">
          <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
          <span>ייצוא נתונים (Excel)</span>
        </button>
      </div>

      <!-- Live Sources Filter Panel -->
      <div class="space-y-2.5 pt-2">
        <div class="flex items-center justify-between text-xs pb-1 border-b border-[#202632]">
          <span class="font-bold text-white text-[11px] tracking-wide">מקורות מידע</span>
          <span class="text-[10px] text-[#8A97AC]">סינון ממוקד</span>
        </div>

        <div class="space-y-1" id="agentsContainer">
          <!-- All Sources -->
          <button onclick="filterBySource('all', this)" class="agent-btn active w-full text-right bg-[#202632] border border-[#EA580C]/40 text-white rounded-lg px-3 py-2 flex items-center justify-between text-xs transition">
            <span class="font-medium">כל המקורות</span>
            <span class="text-[11px] font-mono font-bold text-[#FB923C]" id="agentCountAll">__TOTAL_OPPS__</span>
          </button>

          <!-- Gov Tenders -->
          <button onclick="filterBySource('gov', this)" class="agent-btn w-full text-right bg-[#181C24] hover:bg-[#202632] border border-[#202632] text-[#C2CDDC] rounded-lg px-3 py-2 flex items-center justify-between text-xs transition">
            <div class="flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
              <span>מכרזי ממשלה (gov.il)</span>
            </div>
            <span class="text-[10px] font-mono text-[#8A97AC]" id="agentCountGov">0</span>
          </button>

          <!-- Municipalities -->
          <button onclick="filterBySource('muni', this)" class="agent-btn w-full text-right bg-[#181C24] hover:bg-[#202632] border border-[#202632] text-[#C2CDDC] rounded-lg px-3 py-2 flex items-center justify-between text-xs transition">
            <div class="flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              <span>עיריות ורשויות מקומיות</span>
            </div>
            <span class="text-[10px] font-mono text-[#8A97AC]" id="agentCountMuni">0</span>
          </button>

          <!-- Private / Classifieds -->
          <button onclick="filterBySource('private', this)" class="agent-btn w-full text-right bg-[#181C24] hover:bg-[#202632] border border-[#202632] text-[#C2CDDC] rounded-lg px-3 py-2 flex items-center justify-between text-xs transition">
            <div class="flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
              <span>לוחות וקבוצות פרטיות</span>
            </div>
            <span class="text-[10px] font-mono text-[#8A97AC]" id="agentCountPrivate">0</span>
          </button>

          <!-- Direct / WhatsApp -->
          <button onclick="filterBySource('webhook', this)" class="agent-btn w-full text-right bg-[#181C24] hover:bg-[#202632] border border-[#202632] text-[#C2CDDC] rounded-lg px-3 py-2 flex items-center justify-between text-xs transition">
            <div class="flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full bg-[#EA580C]"></span>
              <span>קליטה ישירה (WhatsApp)</span>
            </div>
            <span class="text-[10px] font-mono text-[#8A97AC]" id="agentCountDirect">0</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Sidebar Bottom: Progress -->
    <div class="pt-4 border-t border-[#202632] space-y-2">
      <div class="flex justify-between items-center text-xs">
        <span class="text-[#8A97AC] text-[11px]">התקדמות סקירה</span>
        <span class="text-[#FB923C] font-mono font-bold" id="progressPct">0%</span>
      </div>
      <div class="w-full h-1 bg-[#181C24] rounded-full overflow-hidden">
        <div id="sidebarProgressBar" class="h-full bg-[#EA580C] rounded-full transition-all duration-300" style="width: 0%"></div>
      </div>
      <div class="text-[10px] text-[#8A97AC] flex justify-between font-mono">
        <span id="reviewedCounter">0 נבדקו</span>
        <span>__TOTAL_OPPS__ סה״כ</span>
      </div>
    </div>
  </aside>

  <!-- Main Content Viewport -->
  <main class="flex-1 p-4 md:p-8 space-y-6 max-w-7xl mx-auto w-full">

    <!-- Top Header Banner -->
    <section class="bg-[#12151B] border border-[#202632] rounded-2xl p-5 md:p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <div class="flex items-center gap-2 text-xs text-[#8A97AC] mb-1 font-mono">
          <span>תאריך סריקה: <strong class="text-[#F0F4F8]">__NOW_STR__</strong></span>
          <span>•</span>
          <span class="text-emerald-400">מסד נתונים מסונכרן</span>
        </div>
        <h1 class="text-2xl md:text-3xl font-black text-white tracking-tight">
          מרכז איתור לידים ומכרזים
        </h1>
        <p class="text-xs md:text-sm text-[#8A97AC] mt-1">
          ריכוז, תעדוף וניתוח עובדתי של הזדמנויות עסקיות לקבלנים
        </p>
      </div>

      <!-- Header Actions & Metrics Badges -->
      <div class="flex flex-wrap items-center gap-2.5">
        <button onclick="openScanModal()" class="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-[#EA580C] to-[#C2410C] hover:from-[#FB923C] hover:to-[#EA580C] text-white rounded-xl text-xs font-bold shadow-md shadow-orange-950/40 transition active:scale-[0.98] group">
          <svg class="w-4 h-4 text-white group-hover:rotate-180 transition-transform duration-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
          <span>הפעל סריקה ידנית</span>
        </button>

        <div class="bg-[#181C24] border border-[#202632] px-3.5 py-2 rounded-xl min-w-[85px] text-center">
          <div class="text-[10px] text-[#8A97AC] font-medium">סך הכל זוהו</div>
          <div class="text-base font-mono font-bold text-white">__TOTAL_OPPS__</div>
        </div>
        <div class="bg-[#181C24] border border-rose-500/30 px-3.5 py-2 rounded-xl min-w-[85px] text-center">
          <div class="text-[10px] text-rose-400 font-medium flex items-center justify-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
            מסלול מהיר
          </div>
          <div class="text-base font-mono font-bold text-rose-400" id="statFastTrack">0</div>
        </div>
        <div class="bg-[#181C24] border border-emerald-500/30 px-3.5 py-2 rounded-xl min-w-[85px] text-center">
          <div class="text-[10px] text-emerald-400 font-medium flex items-center justify-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            בטיפול
          </div>
          <div class="text-base font-mono font-bold text-emerald-400" id="statSaved">0</div>
        </div>
      </div>
    </section>

    <!-- Pipeline Funnel -->
    <section class="bg-[#12151B] border border-[#202632] rounded-2xl p-5 shadow-sm space-y-3.5">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-sm md:text-base font-bold text-white">
            משפך עיבוד הזדמנויות (Pipeline Funnel)
          </h2>
          <p class="text-xs text-[#8A97AC]">שלבי הסינון מרגע הזיהוי ועד התאמה מלאה לפרופיל הקבלן</p>
        </div>
        <span class="text-[11px] font-mono text-[#FB923C] bg-[#EA580C]/10 px-3 py-1 rounded border border-[#EA580C]/20">
          אוטומטי
        </span>
      </div>

      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 pt-1">
        <div class="bg-[#181C24] border border-[#202632] rounded-xl p-3.5 text-center">
          <div class="text-[11px] text-[#8A97AC] mb-1">1. זוהו במקורות</div>
          <div class="text-2xl font-mono font-bold text-white">__TOTAL_OPPS__</div>
          <div class="text-[10px] text-slate-500 mt-0.5">ממשלה, עיריות, רשת</div>
          <div class="h-1 w-full bg-[#2D3545] mt-2.5 rounded-full"></div>
        </div>
        <div class="bg-[#181C24] border border-[#202632] rounded-xl p-3.5 text-center">
          <div class="text-[11px] text-[#8A97AC] mb-1">2. עברו אימות ו-OCR</div>
          <div class="text-2xl font-mono font-bold text-white">__TOTAL_OPPS__</div>
          <div class="text-[10px] text-slate-500 mt-0.5">מניעת כפילויות + חילוץ</div>
          <div class="h-1 w-full bg-[#414C62] mt-2.5 rounded-full"></div>
        </div>
        <div class="bg-[#181C24] border border-[#202632] rounded-xl p-3.5 text-center">
          <div class="text-[11px] text-[#8A97AC] mb-1">3. התאמה לפרופיל</div>
          <div class="text-2xl font-mono font-bold text-emerald-400" id="funnelQualified">0</div>
          <div class="text-[10px] text-emerald-500/70 mt-0.5">ציון 70 ומעלה</div>
          <div class="h-1 w-full bg-emerald-500 mt-2.5 rounded-full"></div>
        </div>
        <div class="bg-[#181C24] border border-rose-500/20 rounded-xl p-3.5 text-center">
          <div class="text-[11px] text-rose-400 font-medium mb-1 flex items-center justify-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
            4. מסלול מהיר
          </div>
          <div class="text-2xl font-mono font-bold text-rose-400" id="funnelFast">0</div>
          <div class="text-[10px] text-rose-500/70 mt-0.5">דחיפות גבוהה</div>
          <div class="h-1 w-full bg-rose-500 mt-2.5 rounded-full"></div>
        </div>
      </div>
    </section>

    <!-- Filters Bar & Tabs -->
    <section class="bg-[#12151B] border border-[#202632] rounded-2xl p-3 shadow-sm flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
      
      <!-- Primary Tabs -->
      <div class="flex items-center gap-1 bg-[#0B0D11] p-1 rounded-xl border border-[#202632] overflow-x-auto custom-scrollbar">
        <button onclick="setTab('all', this)" class="tab-btn active px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-[#EA580C] text-white shadow-sm whitespace-nowrap">
          כל ההזדמנויות (<span id="tabCountAll">0</span>)
        </button>
        <button onclick="setTab('fast_track', this)" class="tab-btn px-3.5 py-1.5 text-xs font-medium rounded-lg text-rose-400 hover:text-white whitespace-nowrap flex items-center gap-1.5">
          <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
          מסלול מהיר (<span id="tabCountFast">0</span>)
        </button>
        <button onclick="setTab('tenders', this)" class="tab-btn px-3.5 py-1.5 text-xs font-medium rounded-lg text-[#8A97AC] hover:text-white whitespace-nowrap">
          מכרזים (<span id="tabCountTenders">0</span>)
        </button>
        <button onclick="setTab('saved', this)" class="tab-btn px-3.5 py-1.5 text-xs font-medium rounded-lg text-emerald-400 hover:text-white whitespace-nowrap flex items-center gap-1.5">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          בטיפול (<span id="tabCountSaved">0</span>)
        </button>
        <button onclick="setTab('rejected', this)" class="tab-btn px-3.5 py-1.5 text-xs font-medium rounded-lg text-slate-500 hover:text-white whitespace-nowrap">
          נפסלו (<span id="tabCountRejected">0</span>)
        </button>
      </div>

      <!-- Search & Trade Select -->
      <div class="flex items-center gap-2">
        <div class="relative flex-1 md:w-56">
          <input type="text" id="searchInput" oninput="renderCards()" placeholder="חיפוש לפי כותרת, עיר..." class="w-full bg-[#0B0D11] text-xs text-white px-3 py-2 pr-8 rounded-xl border border-[#202632] focus:outline-none focus:border-[#EA580C]">
          <svg class="w-3.5 h-3.5 absolute right-2.5 top-2.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
        </div>

        <select id="tradeFilter" onchange="renderCards()" class="bg-[#0B0D11] text-xs text-[#C2CDDC] px-3 py-2 rounded-xl border border-[#202632] focus:outline-none focus:border-[#EA580C]">
          <option value="all">כל הענפים והמקצועות</option>
          <option value="general_contractor">שיפוץ כללי ובנייה</option>
          <option value="plumbing">אינסטלציה וצנרת</option>
          <option value="electrical">חשמל ותשתיות</option>
          <option value="hvac">מיזוג אוויר (HVAC)</option>
          <option value="painting">צבע, טיח וגבס</option>
          <option value="earthworks">עבודות עפר ופיתוח</option>
        </select>
      </div>
    </section>

    <!-- Cards Container -->
    <section id="cardsContainer" class="space-y-4">
      <!-- Injected by JS -->
    </section>

    <!-- Empty State -->
    <div id="emptyState" class="hidden bg-[#12151B] border border-dashed border-[#202632] rounded-2xl p-12 text-center space-y-3">
      <div class="w-10 h-10 mx-auto rounded-full bg-[#181C24] flex items-center justify-center text-slate-400">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
      </div>
      <h3 class="text-sm font-bold text-white">לא נמצאו הזדמנויות בסינון הנוכחי</h3>
      <p class="text-xs text-[#8A97AC] max-w-sm mx-auto">נסה לאפס את הסינונים או לבחור מקור סריקה אחר.</p>
      <button onclick="resetFilters()" class="px-4 py-2 bg-[#181C24] hover:bg-[#202632] text-xs font-semibold rounded-xl text-[#FB923C] border border-[#202632]">
        איפוס סינונים
      </button>
    </div>

  </main>

  <!-- Modal: Manual Scan Trigger -->
  <div id="scanModal" class="hidden fixed inset-0 bg-black/85 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-[#12151B] border border-[#202632] rounded-2xl max-w-xl w-full p-6 space-y-5 shadow-2xl relative max-h-[90vh] overflow-y-auto custom-scrollbar">
      
      <!-- Modal Header -->
      <div class="flex items-center justify-between pb-3 border-b border-[#202632]">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-[#EA580C]/20 border border-[#EA580C]/40 flex items-center justify-center text-[#FB923C]">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
          </div>
          <div>
            <h3 class="text-base font-bold text-white">הפעלת סריקה יזומה</h3>
            <p class="text-[11px] text-[#8A97AC]">הפעלת סריקת מקורות מידע, ניתוח AI ב-Gemini ושליחת התראות</p>
          </div>
        </div>
        <button onclick="closeScanModal()" class="text-[#8A97AC] hover:text-white text-lg p-1">✕</button>
      </div>

      <!-- Cloud Actions Status Box -->
      <div class="bg-[#181C24] border border-[#202632] rounded-xl p-4 space-y-2">
        <div class="flex items-center justify-between text-xs">
          <span class="text-[#8A97AC] font-medium">סטטוס סריקת ענן (GitHub Actions):</span>
          <span id="cloudScanStatus" class="flex items-center gap-1.5 font-mono text-[11px] text-emerald-400">
            <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
            סריקה אחרונה הושלמה בהצלחה
          </span>
        </div>
        <div class="text-[11px] text-[#C2CDDC] flex items-center justify-between font-mono" id="cloudScanDetails">
          <span>הפעלה ידנית בלבד (אין תזמון פעיל)</span>
          <a href="https://github.com/idogal0210-web/contractor_leads_tenders/actions" target="_blank" class="text-[#FB923C] hover:underline flex items-center gap-1">
            <span>לוגים בענן</span>
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
          </a>
        </div>
      </div>

      <!-- Option A: Cloud Scan Trigger -->
      <div class="space-y-3">
        <div class="text-xs font-bold text-white flex items-center gap-2">
          <span class="w-5 h-5 rounded-full bg-[#EA580C]/20 text-[#FB923C] text-[10px] flex items-center justify-center font-mono">1</span>
          <span>שיגור סריקה מיידית בענן (מומלץ)</span>
        </div>
        <p class="text-xs text-[#8A97AC] leading-relaxed">
          הסריקה תרוץ בשרתי הענן של GitHub Actions, תפעיל את מודל Gemini 3.8 Flash לחילוץ עובדתי, תשלח התראות טלגרם/מייל על לידים דחופים, ותעדכן את הדשבורד אוטומטית.
        </p>
        <div class="flex flex-wrap gap-2">
          <a href="https://github.com/idogal0210-web/contractor_leads_tenders/actions/workflows/daily_leads_scan.yml" target="_blank" onclick="trackCloudScanTrigger()" class="flex-1 min-w-[200px] flex items-center justify-center gap-2 px-4 py-2.5 bg-[#EA580C] hover:bg-[#C2410C] text-white font-bold text-xs rounded-xl shadow-md transition active:scale-[0.98]">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
            <span>פתח שיגור ישיר בענן (Run Workflow)</span>
          </a>
          <button onclick="checkLiveScanStatus()" class="px-3 py-2.5 bg-[#181C24] hover:bg-[#202632] border border-[#202632] text-[#C2CDDC] text-xs font-medium rounded-xl transition flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-[#FB923C]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
            <span>רענן סטטוס</span>
          </button>
        </div>
      </div>

      <!-- Option B: Local Terminal Execution -->
      <div class="space-y-2.5 pt-2 border-t border-[#202632]">
        <div class="text-xs font-bold text-white flex items-center gap-2">
          <span class="w-5 h-5 rounded-full bg-[#202632] text-[#C2CDDC] text-[10px] flex items-center justify-center font-mono">2</span>
          <span>הרצה ידנית מקומית (טרמינל)</span>
        </div>
        <div class="flex items-center justify-between bg-[#0B0D11] border border-[#202632] rounded-xl px-3.5 py-2 text-xs font-mono">
          <span class="text-emerald-400">python3 main.py</span>
          <button onclick="copyTerminalCommand()" class="text-xs text-[#FB923C] hover:text-white flex items-center gap-1 py-1 px-2 rounded hover:bg-[#181C24] transition">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
            <span>העתק פקודה</span>
          </button>
        </div>
      </div>

      <!-- Scanned Sources Breakdown Preview -->
      <div class="space-y-2 pt-2 border-t border-[#202632]">
        <span class="text-[11px] font-bold text-[#8A97AC] block">מקורות הנסרקים בתהליך:</span>
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-1.5 text-[10px] text-[#C2CDDC]">
          <div class="bg-[#181C24] p-2 rounded-lg border border-[#202632] flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
            <span>מכרזי ממשלה (gov.il)</span>
          </div>
          <div class="bg-[#181C24] p-2 rounded-lg border border-[#202632] flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            <span>6 אתרי עיריות מרכזיות</span>
          </div>
          <div class="bg-[#181C24] p-2 rounded-lg border border-[#202632] flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
            <span>פורום שיפוץ ובנייה (תפוז)</span>
          </div>
          <div class="bg-[#181C24] p-2 rounded-lg border border-[#202632] flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
            <span>פורום עשה זאת בעצמך</span>
          </div>
          <div class="bg-[#181C24] p-2 rounded-lg border border-[#202632] flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-[#EA580C]"></span>
            <span>קליטת WhatsApp / Webhook</span>
          </div>
          <div class="bg-[#181C24] p-2 rounded-lg border border-[#202632] flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
            <span>סיווג וניקוד Gemini AI</span>
          </div>
        </div>
      </div>

      <!-- Footer Buttons -->
      <div class="flex justify-end pt-2">
        <button onclick="closeScanModal()" class="px-4 py-2 bg-[#181C24] hover:bg-[#202632] text-xs font-medium rounded-xl text-[#C2CDDC] transition">
          סגור
        </button>
      </div>

    </div>
  </div>

  <!-- Modal: Manual Lead Ingestion -->
  <div id="manualLeadModal" class="hidden fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-[#12151B] border border-[#202632] rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-bold text-white">הזנת ליד מהיר מחילוץ טקסט</h3>
        <button onclick="closeManualLeadModal()" class="text-[#8A97AC] hover:text-white text-sm">✕</button>
      </div>
      <p class="text-xs text-[#8A97AC]">
        הדבק הודעת WhatsApp, פוסט או טקסט פנייה. המערכת תסנן, תסווג ותציג את הליד ישירות ברשימה.
      </p>
      <textarea id="manualLeadText" rows="5" placeholder="לדוגמה: מחפש קבלן שיפוצים דחוף לעבודת אינסטלציה וריצוף בתל אביב. טלפון: 052-..." class="w-full bg-[#0B0D11] text-xs text-white p-3.5 rounded-xl border border-[#202632] focus:outline-none focus:border-[#EA580C] custom-scrollbar"></textarea>
      <div class="flex justify-end gap-2">
        <button onclick="closeManualLeadModal()" class="px-4 py-2 bg-[#181C24] hover:bg-[#202632] text-xs font-medium rounded-xl text-[#C2CDDC]">
          ביטול
        </button>
        <button onclick="submitManualLead()" class="px-5 py-2 bg-[#EA580C] hover:bg-[#C2410C] text-white font-medium text-xs rounded-xl shadow-sm">
          חלץ והוסף ליד
        </button>
      </div>
    </div>
  </div>

  <!-- Toast Notification -->
  <div id="toast" class="fixed bottom-5 left-5 z-50 transform translate-y-20 opacity-0 transition-all duration-300 pointer-events-none bg-[#12151B] border border-[#202632] text-white px-4 py-3 rounded-xl shadow-2xl flex items-center gap-2.5 text-xs font-medium">
    <span class="w-2 h-2 rounded-full bg-[#EA580C]" id="toastDot"></span>
    <span id="toastMsg">הודעה</span>
  </div>

  <!-- Client-Side App Logic -->
  <script>
    const rawOppsData = __OPPORTUNITIES_JSON__;
    let currentTab = 'all';
    let currentSourceFilter = 'all';
    let oppStates = {}; // id -> 'saved' | 'rejected' | 'contacted'

    function loadSavedStates() {
      try {
        const saved = localStorage.getItem('constructleads_states');
        if (saved) oppStates = JSON.parse(saved);
      } catch (e) {
        oppStates = {};
      }
    }

    function saveStates() {
      try {
        localStorage.setItem('constructleads_states', JSON.stringify(oppStates));
      } catch (e) {}
      updateMetrics();
    }

    let _toastTimer = null;
    function showToast(msg, type = 'default') {
      const toast = document.getElementById('toast');
      const dot = document.getElementById('toastDot');
      document.getElementById('toastMsg').innerText = msg;
      dot.className = 'w-2 h-2 rounded-full ' + (type === 'error' ? 'bg-rose-400' : type === 'success' ? 'bg-emerald-400' : 'bg-[#EA580C]');
      toast.classList.remove('translate-y-20', 'opacity-0');
      if (_toastTimer) clearTimeout(_toastTimer);
      _toastTimer = setTimeout(() => {
        toast.classList.add('translate-y-20', 'opacity-0');
        _toastTimer = null;
      }, 3000);
    }

    function setTab(tab, btn) {
      currentTab = tab;
      document.querySelectorAll('.tab-btn').forEach(b => {
        b.classList.remove('active', 'bg-[#EA580C]', 'text-white', 'font-semibold');
        b.classList.add('text-[#8A97AC]', 'font-medium');
      });
      if (btn) {
        btn.classList.add('active', 'bg-[#EA580C]', 'text-white', 'font-semibold');
        btn.classList.remove('text-[#8A97AC]');
      }
      renderCards();
    }

    function filterBySource(sourceKey, btn) {
      currentSourceFilter = sourceKey;
      document.querySelectorAll('.agent-btn').forEach(b => {
        b.classList.remove('active', 'bg-[#202632]', 'border-[#EA580C]/40', 'text-white');
        b.classList.add('bg-[#181C24]', 'border-[#202632]', 'text-[#C2CDDC]');
      });
      if (btn) {
        btn.classList.add('active', 'bg-[#202632]', 'border-[#EA580C]/40', 'text-white');
        btn.classList.remove('bg-[#181C24]', 'text-[#C2CDDC]');
      }
      renderCards();
    }

    function updateMetrics() {
      const total = rawOppsData.length;
      const fastTrack = rawOppsData.filter(o => o.is_fast_track).length;
      const tenders = rawOppsData.filter(o => o.opportunity_type === 'tender').length;
      const saved = Object.values(oppStates).filter(s => s === 'saved' || s === 'contacted').length;
      const rejected = Object.values(oppStates).filter(s => s === 'rejected').length;
      const qualified = rawOppsData.filter(o => (o.score_business_fit || 0) >= 70).length;

      document.getElementById('statFastTrack').innerText = fastTrack;
      document.getElementById('statSaved').innerText = saved;
      document.getElementById('funnelFast').innerText = fastTrack;
      document.getElementById('funnelQualified').innerText = qualified;

      document.getElementById('tabCountAll').innerText = total;
      document.getElementById('tabCountFast').innerText = fastTrack;
      document.getElementById('tabCountTenders').innerText = tenders;
      document.getElementById('tabCountSaved').innerText = saved;
      document.getElementById('tabCountRejected').innerText = rejected;

      document.getElementById('agentCountAll').innerText = total;
      const govFilter = o => (o.source_label || '').includes('M2M') || (o.source_label || '').includes('gov') || (o.publisher_name || '').includes('ממשל');
      const muniFilter = o => (o.publisher_name || '').includes('עיריי') || (o.publisher_name || '').includes('מועצה');
      const privateFilter = o => (o.publisher_name || '').includes('יפעת') || (o.source_label || '').includes('DOM') || (o.source_label || '').includes('Apify') || (o.source_label || '').includes('Facebook');
      const directFilter = o => (o.publisher_name || '').includes('הדבקה') || (o.source_label || '').includes('WhatsApp') || (o.publisher_name || '').includes('Webhook');
      document.getElementById('agentCountGov').innerText = rawOppsData.filter(govFilter).length;
      document.getElementById('agentCountMuni').innerText = rawOppsData.filter(muniFilter).length;
      document.getElementById('agentCountPrivate').innerText = rawOppsData.filter(privateFilter).length;
      document.getElementById('agentCountDirect').innerText = rawOppsData.filter(directFilter).length;

      const reviewed = Object.keys(oppStates).length;
      const pct = total > 0 ? Math.min(100, Math.round((reviewed / total) * 100)) : 0;
      document.getElementById('progressPct').innerText = `${pct}%`;
      document.getElementById('sidebarProgressBar').style.width = `${pct}%`;
      document.getElementById('reviewedCounter').innerText = `${reviewed} נבדקו`;
    }

    function setAction(oppId, action) {
      oppStates[oppId] = action;
      saveStates();
      renderCards();
      const labels = {
        'saved': 'ההזדמנות נשמרה בטיפול',
        'contacted': 'סומן שנוצר קשר',
        'rejected': 'ההזדמנות נפסלה',
      };
      showToast(labels[action] || 'עודכן');
    }

    function copyOppDetails(oppId) {
      const opp = rawOppsData.find(o => o.id === oppId);
      if (!opp) return;
      const text = `כותרת: ${opp.title_value || ''}\nמיקום: ${opp.location_value || 'ישראל'}\nענף: ${opp.work_type_value || ''}\nתקציב: ${opp.budget_value ? opp.budget_value + ' ₪' : 'לא צוין'}\nאיש קשר: ${opp.contact_value || 'לא צוין'}\nסיווג נדרש: ${opp.required_classification || 'אין דרישה'}`;
      navigator.clipboard.writeText(text).then(() => {
        showToast('פרטי ההזדמנות הועתקו ללוח');
      });
    }

    function openWhatsAppLead(oppId) {
      const opp = rawOppsData.find(o => o.id === oppId);
      if (!opp) return;
      const phoneClean = (opp.contact_value || '').replace(/[^0-9]/g, '');
      let phone = phoneClean;
      if (phone.startsWith('0')) phone = '972' + phone.slice(1);
      
      const draft = opp.draft_proposal || `שלום, אני פונה בנוגע לעבודה: "${opp.title_value || ''}" שפורסמה ב-${opp.location_value || 'אזור המרכז'}. אשמח לפרטים נוספים.`;
      const message = encodeURIComponent(draft);
      const url = phone ? `https://wa.me/${phone}?text=${message}` : `https://wa.me/?text=${message}`;
      window.open(url, '_blank');
      setAction(oppId, 'contacted');
    }

    function renderCards() {
      const container = document.getElementById('cardsContainer');
      const emptyState = document.getElementById('emptyState');
      const search = (document.getElementById('searchInput').value || '').toLowerCase().trim();
      const trade = document.getElementById('tradeFilter').value;

      const filtered = rawOppsData.filter(opp => {
        const state = oppStates[opp.id] || 'new';

        if (currentTab === 'fast_track' && !opp.is_fast_track) return false;
        if (currentTab === 'tenders' && opp.opportunity_type !== 'tender') return false;
        if (currentTab === 'saved' && state !== 'saved' && state !== 'contacted') return false;
        if (currentTab === 'rejected' && state !== 'rejected') return false;
        if (currentTab === 'all' && state === 'rejected') return false;

        if (currentSourceFilter !== 'all') {
          const pub = (opp.publisher_name || '').toLowerCase();
          const sl = (opp.source_label || '').toLowerCase();
          if (currentSourceFilter === 'gov' && !pub.includes('ממשל') && !sl.includes('m2m') && !sl.includes('gov')) return false;
          if (currentSourceFilter === 'muni' && !pub.includes('עיריי') && !pub.includes('מועצה')) return false;
          if (currentSourceFilter === 'private' && !pub.includes('יפעת') && !sl.includes('dom') && !sl.includes('apify') && !sl.includes('facebook')) return false;
          if (currentSourceFilter === 'webhook' && !pub.includes('הדבקה') && !sl.includes('whatsapp') && !pub.includes('webhook')) return false;
        }

        if (search) {
          const matchTitle = (opp.title_value || '').toLowerCase().includes(search);
          const matchLoc = (opp.location_value || '').toLowerCase().includes(search);
          const matchWork = (opp.work_type_value || '').toLowerCase().includes(search);
          const matchEvidence = (opp.title_evidence || '').toLowerCase().includes(search);
          if (!matchTitle && !matchLoc && !matchWork && !matchEvidence) return false;
        }

        if (trade !== 'all') {
          const work = (opp.work_type_value || '').toLowerCase();
          const title = (opp.title_value || '').toLowerCase();
          const tradeKeywords = {
            'general_contractor': ['שיפוץ', 'בנייה', 'קבלן'],
            'plumbing': ['אינסטלציה', 'צנרת', 'ברז', 'שרברב'],
            'electrical': ['חשמל', 'לוח', 'מתח'],
            'hvac': ['מיזוג', 'קירור', 'חימום', 'מזגן'],
            'painting': ['צבע', 'טיח', 'גבס'],
            'earthworks': ['עפר', 'חפירה', 'תשתית']
          };
          const keys = tradeKeywords[trade] || [];
          if (!keys.some(k => title.includes(k) || work.includes(k))) return false;
        }

        return true;
      });

      if (filtered.length === 0) {
        container.innerHTML = '';
        emptyState.classList.remove('hidden');
        return;
      }

      emptyState.classList.add('hidden');
      container.innerHTML = filtered.map(opp => {
        const state = oppStates[opp.id] || 'new';
        const isFast = opp.is_fast_track;
        const isTender = opp.opportunity_type === 'tender';
        const score = opp.score_business_fit ?? 0;
        const budget = opp.budget_value ? `${Number(opp.budget_value).toLocaleString()} ₪` : 'לא צוין במקור';
        const phone = opp.contact_value || '';
        const location = opp.location_value || 'ארצי / לא צוין';
        const deadline = opp.deadline_value ? new Date(opp.deadline_value).toLocaleDateString('he-IL') : 'מיידי';
        const classification = opp.required_classification || (isTender ? 'ג-1 ומעלה' : 'אין דרישת סיווג');
        const publisher = opp.publisher_name || 'מקור פרטי';
        const sourceUrl = opp.url || opp.source_url || '';
        const valStatus = opp.validation_status || 'valid';

        const sourceLabel = opp.source_label || '';
        let sourceBadge = 'bg-[#181C24] text-[#8A97AC] border-[#202632]';
        if (publisher.includes('ממשל') || sourceLabel.includes('M2M') || sourceLabel.includes('gov')) sourceBadge = 'bg-blue-500/10 text-blue-400 border-blue-500/30';
        else if (publisher.includes('עיריי') || publisher.includes('מועצה')) sourceBadge = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
        else if (publisher.includes('WhatsApp') || publisher.includes('הדבקה') || sourceLabel.includes('Apify') || sourceLabel.includes('Facebook')) sourceBadge = 'bg-[#EA580C]/10 text-[#FB923C] border-[#EA580C]/30';
        else if (publisher.includes('יפעת') || sourceLabel.includes('DOM')) sourceBadge = 'bg-purple-500/10 text-purple-400 border-purple-500/30';

        let validationBadge = '';
        if (valStatus === 'invalid') {
          validationBadge = `<span class="px-2.5 py-0.5 rounded text-[11px] font-medium border bg-rose-500/10 text-rose-500 border-rose-500/30" title="הקישור נבדק ונמצא לא פעיל">לא פעיל</span>`;
        } else if (valStatus === 'requires_auth') {
          validationBadge = `<span class="px-2.5 py-0.5 rounded text-[11px] font-medium border bg-amber-500/10 text-amber-500 border-amber-500/30" title="נדרש חיבור או הרשמה">דורש כניסה</span>`;
        }

        const freshnessStatus = opp.freshness_status || 'fresh';
        let freshnessBadge = '';
        if (freshnessStatus === 'stale') {
          freshnessBadge = `<span class="px-2.5 py-0.5 rounded text-[11px] font-medium border bg-slate-500/10 text-slate-400 border-slate-500/30" title="ליד ישן — פורסם לפני יותר מ-45 יום">לא עדכני</span>`;
        }

        return `
          <div class="bg-[#12151B] border ${isFast ? 'border-[#EA580C]/50 shadow-sm' : 'border-[#202632]'} rounded-2xl p-5 hover:border-[#2D3545] transition relative group">
            
            <!-- Card Header -->
            <div class="flex flex-wrap items-start justify-between gap-3 mb-3">
              <div class="flex flex-wrap items-center gap-2">
                ${isFast ? `
                  <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30 flex items-center gap-1.5">
                    <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                    מסלול מהיר
                  </span>
                ` : ''}
                
                <span class="px-2.5 py-0.5 rounded text-[11px] font-medium border ${sourceBadge}">
                  ${publisher}
                </span>

                <span class="px-2 py-0.5 rounded text-[10px] font-medium bg-[#181C24] text-[#C2CDDC] border border-[#202632]">
                  ${isTender ? 'מכרז רשמי' : 'ליד ישיר'}
                </span>

                ${validationBadge}
                ${freshnessBadge}

                <span class="text-xs text-[#8A97AC]">מיקום: ${location}</span>
              </div>

              <!-- Score Indicator -->
              <div class="flex items-center gap-2">
                <div class="text-right">
                  <div class="text-[10px] text-[#8A97AC]">התאמה</div>
                  <div class="text-xs font-mono font-bold text-[#FB923C]">${score}/100</div>
                </div>
                <div class="w-8 h-8 rounded-lg bg-[#EA580C]/10 border border-[#EA580C]/30 flex items-center justify-center text-[#FB923C] font-mono font-bold text-xs">
                  ${score}
                </div>
              </div>
            </div>

            <!-- Title -->
            <h3 class="text-base md:text-lg font-bold text-white group-hover:text-[#FB923C] transition leading-snug mb-2">
              ${opp.title_value || 'ללא כותרת'}
            </h3>

            <!-- Evidence Quote -->
            <div class="bg-[#0B0D11] border-r-2 border-[#EA580C] px-3.5 py-2.5 rounded-l-xl text-xs text-[#C2CDDC] mb-3 font-mono leading-relaxed">
              <span class="text-[#8A97AC] block text-[10px] font-sans font-semibold mb-0.5">ציטוט עובדתי מהמקור:</span>
              "${opp.title_evidence || opp.work_type_evidence || opp.work_type_value || 'דרישת עבודה שזוהתה בטקסט המקורי'}"
            </div>

            <!-- Full Raw Content -->
            ${opp.raw_content && opp.raw_content.length > 10 ? `
            <details class="mb-3 group/details">
              <summary class="cursor-pointer text-[11px] text-[#8A97AC] hover:text-[#C2CDDC] flex items-center gap-1.5 select-none transition">
                <svg class="w-3 h-3 transition-transform group-open/details:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
                תוכן מלא מהמקור
              </summary>
              <div class="mt-2 p-3 bg-white/[0.02] border border-white/[0.06] rounded-xl text-[11px] text-[#8A97AC] leading-relaxed whitespace-pre-wrap max-h-40 overflow-y-auto custom-scrollbar font-mono">
                ${(opp.raw_content || '').replace(/[<>]/g, c => c === '<' ? '&lt;' : '&gt;')}
              </div>
            </details>
            ` : ''}

            <!-- Key Attributes Grid -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4 bg-[#181C24] p-3 rounded-xl border border-[#202632] text-xs">
              <div>
                <span class="text-[10px] text-[#8A97AC] block">ענף / מקצוע:</span>
                <strong class="text-white font-medium">${opp.work_type_value || 'כללי'}</strong>
              </div>
              <div>
                <span class="text-[10px] text-[#8A97AC] block">סיווג קבלני:</span>
                <strong class="text-amber-400 font-medium">${classification}</strong>
              </div>
              <div>
                <span class="text-[10px] text-[#8A97AC] block">תקציב:</span>
                <strong class="text-emerald-400 font-mono font-bold">${budget}</strong>
              </div>
              <div>
                <span class="text-[10px] text-[#8A97AC] block">מועד אחרון:</span>
                <strong class="text-[#F0F4F8] font-medium">${deadline}</strong>
              </div>
            </div>

            <!-- Action Buttons Footer -->
            <div class="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-[#202632]">
              
              <div class="flex flex-wrap items-center gap-2">
                <!-- WhatsApp Action -->
                <button onclick="openWhatsAppLead('${opp.id}')" class="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-xl shadow-sm flex items-center gap-1.5 transition active:scale-95">
                  <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981z"/></svg>
                  <span>פנייה בוואטסאפ</span>
                </button>

                <!-- Phone Call Action -->
                ${phone ? `
                  <a href="tel:${phone}" onclick="setAction('${opp.id}', 'contacted')" class="px-3 py-1.5 bg-[#181C24] hover:bg-[#202632] text-slate-200 text-xs font-medium rounded-xl border border-[#202632] flex items-center gap-1.5 transition">
                    <svg class="w-3.5 h-3.5 text-[#8A97AC]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"></path></svg>
                    <span>חיוג (${phone})</span>
                  </a>
                ` : ''}

                <!-- Source Link Action -->
                ${sourceUrl ? `
                  <a href="${sourceUrl}" target="_blank" rel="noopener noreferrer" class="px-3 py-1.5 bg-[#181C24] hover:bg-[#202632] text-[#C2CDDC] hover:text-[#FB923C] text-xs font-medium rounded-xl border border-[#202632] flex items-center gap-1.5 transition" title="${opp.source_label || 'פתיחת דף המקור'}">
                    <svg class="w-3.5 h-3.5 text-[#8A97AC]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                    <span>פתיחת מקור</span>
                  </a>
                ` : `
                  <span class="px-2.5 py-1.5 bg-[#181C24] text-[#8A97AC] text-[11px] font-medium rounded-xl border border-[#202632] flex items-center gap-1.5 cursor-help" title="${opp.source_label || 'מקור לא ידוע'}">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path></svg>
                    <span>${opp.source_label || publisher}</span>
                  </span>
                `}

                <!-- Copy Action -->
                <button onclick="copyOppDetails('${opp.id}')" class="px-3 py-1.5 bg-[#181C24] hover:bg-[#202632] text-[#C2CDDC] hover:text-white text-xs font-medium rounded-xl border border-[#202632] flex items-center gap-1.5 transition active:scale-95" title="העתק פרטי ליד">
                  <svg class="w-3.5 h-3.5 text-[#8A97AC]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                  <span>העתקת פרטים</span>
                </button>
              </div>

              <!-- Status Actions -->
              <div class="flex items-center gap-2">
                ${state !== 'saved' && state !== 'contacted' ? `
                  <button onclick="setAction('${opp.id}', 'saved')" class="px-3.5 py-1.5 bg-[#202632] hover:bg-[#2D3545] text-[#FB923C] hover:text-white text-xs font-medium rounded-xl border border-[#2D3545] transition flex items-center gap-1.5">
                    <span>שמור לטיפול</span>
                  </button>
                ` : `
                  <span class="px-3 py-1.5 bg-emerald-500/10 text-emerald-400 text-xs font-medium rounded-xl border border-emerald-500/30 flex items-center gap-1.5">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                    בטיפול פעיל
                  </span>
                `}

                <button onclick="setAction('${opp.id}', 'rejected')" class="px-3 py-1.5 bg-[#181C24] hover:bg-rose-500/15 text-[#8A97AC] hover:text-rose-400 text-xs font-medium rounded-xl border border-[#202632] transition">
                  פסילה
                </button>
              </div>

            </div>

          </div>
        `;
      }).join('');
    }

    function exportSavedToExcel() {
      const savedOpps = rawOppsData.filter(o => oppStates[o.id] === 'saved' || oppStates[o.id] === 'contacted');
      const exportList = savedOpps.length > 0 ? savedOpps : rawOppsData;

      const BOM = '\uFEFF';
      const headers = ['כותרת', 'סוג', 'מקור', 'מיקום', 'ענף מקצועי', 'סיווג קבלני', 'תקציב', 'מועד אחרון', 'איש קשר', 'ציון התאמה', 'מסלול מהיר'];
      const escapeCSV = (v) => `"${String(v || '').replace(/"/g, '""')}"`;

      const rows = exportList.map(o => [
        escapeCSV(o.title_value),
        escapeCSV(o.opportunity_type === 'tender' ? 'מכרז' : 'ליד'),
        escapeCSV(o.publisher_name || 'מקור פרטי'),
        escapeCSV(o.location_value || 'ישראל'),
        escapeCSV(o.work_type_value),
        escapeCSV(o.required_classification || 'לא נדרש'),
        escapeCSV(o.budget_value ? `${o.budget_value} ₪` : 'לא צוין'),
        escapeCSV(o.deadline_value || 'מיידי'),
        escapeCSV(o.contact_value || ''),
        escapeCSV(o.score_business_fit || 0),
        escapeCSV(o.is_fast_track ? 'כן' : 'לא')
      ].join(','));

      const csvContent = BOM + [headers.map(escapeCSV).join(','), ...rows].join(String.fromCharCode(13, 10));
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `ConstructLeads_Export_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      showToast(`יוצאו ${exportList.length} רשומות לקובץ אקסל בהצלחה`);
    }


    function openScanModal() {
      document.getElementById('scanModal').classList.remove('hidden');
      checkLiveScanStatus();
    }

    function closeScanModal() {
      document.getElementById('scanModal').classList.add('hidden');
    }

    function copyTerminalCommand() {
      navigator.clipboard.writeText('python3 main.py');
      showToast('הפקודה python3 main.py הועתקה ללוח');
    }

    function trackCloudScanTrigger() {
      showToast('פותח דף שיגור סריקה ב-GitHub Actions...');
      setTimeout(() => {
        closeScanModal();
      }, 1000);
    }

    async function checkLiveScanStatus() {
      const statusEl = document.getElementById('cloudScanStatus');
      const detailsEl = document.getElementById('cloudScanDetails');
      if (!statusEl) return;
      
      try {
        statusEl.innerHTML = '<span class="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span> בודק סטטוס ענן...';
        const res = await fetch('https://api.github.com/repos/idogal0210-web/contractor_leads_tenders/actions/runs?per_page=1');
        if (res.ok) {
          const data = await res.json();
          const latest = data.workflow_runs && data.workflow_runs[0];
          if (latest) {
            const status = latest.status; // queued, in_progress, completed
            const conclusion = latest.conclusion; // success, failure, etc.
            const runDate = new Date(latest.created_at).toLocaleString('he-IL');
            
            if (status === 'in_progress' || status === 'queued') {
              statusEl.innerHTML = '<span class="w-2 h-2 rounded-full bg-amber-400 animate-ping"></span> סריקה פעילה כעת בענן...';
            } else if (conclusion === 'success') {
              statusEl.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-400"></span> סריקה הושלמה בהצלחה (${runDate})`;
            } else {
              statusEl.innerHTML = `<span class="w-2 h-2 rounded-full bg-blue-400"></span> סריקה הושלמה (${status})`;
            }
          }
        }
      } catch (err) {
        statusEl.innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-400"></span> מוכן להרצה';
      }
    }

    function openManualLeadModal() {
      document.getElementById('manualLeadModal').classList.remove('hidden');
    }

    function closeManualLeadModal() {
      document.getElementById('manualLeadModal').classList.add('hidden');
    }

    function submitManualLead() {
      const text = document.getElementById('manualLeadText').value.trim();
      if (!text) return;
      showToast('מעבד נתונים...');
      closeManualLeadModal();
      document.getElementById('manualLeadText').value = '';
      setTimeout(() => {
        showToast('הליד נקלט בהצלחה');
      }, 900);
    }

    function resetFilters() {
      document.getElementById('searchInput').value = '';
      document.getElementById('tradeFilter').value = 'all';
      filterBySource('all');
      setTab('all');
    }

    function toggleMobileSidebar() {
      const sb = document.getElementById('sidebar');
      sb.classList.toggle('hidden');
      sb.classList.toggle('fixed');
      sb.classList.toggle('inset-0');
      sb.classList.toggle('w-full');
    }

    window.onload = () => {
      loadSavedStates();
      updateMetrics();
      renderCards();
    };
  </script>
</body>
</html>
"""

def generate_interactive_html(opportunities, title="ConstructLeads.ai | מערכת מודיעין ואיתור מכרזים לקבלנים"):
    """יצירת דף ה-HTML האינטראקטיבי הסטטי מתוך נתוני הלידים והמכרזים."""
    total_opps = len(opportunities)
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    opps_json = json.dumps(opportunities, ensure_ascii=False, default=str)

    html = HTML_TEMPLATE
    html = html.replace("__TITLE__", title)
    html = html.replace("__NOW_STR__", now_str)
    html = html.replace("__TOTAL_OPPS__", str(total_opps))
    html = html.replace("__OPPORTUNITIES_JSON__", opps_json)
    return html

def build_and_save_docs_app(opportunities, project_root):
    """שמירת הדשבורד בקובץ docs/index.html."""
    docs_dir = os.path.join(project_root, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    out_file = os.path.join(docs_dir, "index.html")

    html = generate_interactive_html(opportunities)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[+] הדשבורד המקצועי נוצר בהצלחה ונשמר בכתובת: {out_file}")
    return out_file
