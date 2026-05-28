<template>
  <div class="auth-layout">
    <div class="auth-layout__base" :style="baseBgStyle" aria-hidden="true" />

    <div class="auth-layout__float">
      <div class="auth-layout__float-panel">
        <img
          class="auth-layout__float-img"
          :src="loginFloatBg"
          alt=""
          aria-hidden="true"
        />
        <div class="auth-layout__card-slot">
          <div class="auth-layout__card">
            <div class="auth-layout__brand">
              <img :src="logo" alt="" class="auth-layout__logo-img" />
              <h1 class="auth-layout__title">{{ t('common.appName') }}</h1>
            </div>
            <router-view />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { logo, loginBaseBg, loginFloatBg } from '@/utils/branding'

const { t } = useI18n()

const baseBgStyle = computed(() => ({
  backgroundImage: `url(${loginBaseBg})`,
}))
</script>

<style scoped lang="scss">
.auth-layout {
  position: relative;
  min-height: 100vh;
  width: 100%;
  overflow: hidden;
}

.auth-layout__base {
  position: fixed;
  inset: 0;
  z-index: 0;
  background-color: var(--bg-page-end);
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

.auth-layout__float {
  position: fixed;
  inset: 0;
  z-index: 1;
  pointer-events: none;
}

/* 浮窗：距屏幕四边各 30px，插画填满浮窗 */
.auth-layout__float-panel {
  position: absolute;
  inset: 30px;
  overflow: hidden;
  border-radius: $radius-lg;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  pointer-events: none;
}

.auth-layout__float-img {
  position: absolute;
  inset: 0;
  display: block;
  width: 100%;
  height: 100%;
  object-fit: fill;
  pointer-events: none;
  user-select: none;
}

/*
 * 登录框定位基准 = 浮窗（非全屏）
 * card-slot = 浮窗右半区（50%）
 * card = card-slot 宽度的 50% → 整屏约 25%，但相对右半区确为 1/2
 */
.auth-layout__card-slot {
  position: absolute;
  right: 0;
  top: 0;
  width: 50%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.auth-layout__card {
  position: relative;
  z-index: 2;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  justify-content: center;
  flex-shrink: 0;
  width: 50%;
  height: clamp(360px, 33vh, 620px);
  padding: clamp(24px, 2.5vh, 40px) clamp(24px, 2vw, 36px);
  border-radius: $radius-md;
  background: var(--bg-card);
  border: 1px solid rgba($color-primary, 0.15);
  box-shadow:
    0 12px 40px rgba($color-primary, 0.14),
    0 4px 12px rgba(0, 0, 0, 0.08);
  pointer-events: auto;
}

.auth-layout__brand {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: clamp(16px, 2vh, 28px);
  text-align: left;
}

.auth-layout__logo-img {
  width: 36px;
  height: 36px;
  object-fit: contain;
  flex-shrink: 0;
}

.auth-layout__title {
  margin: 0;
  font-size: clamp(18px, 2.2vh, 24px);
  font-weight: 700;
  color: $text-primary;
  line-height: 1.3;
}

@media (max-width: 767px) {
  .auth-layout__float-panel {
    inset: 12px;
  }

  .auth-layout__card-slot {
    width: 100%;
  }

  .auth-layout__card {
    width: min(92%, 420px);
    height: auto;
    min-height: max(33vh, 380px);
  }

  .auth-layout__brand {
    flex-wrap: wrap;
    justify-content: center;
    text-align: center;
  }
}
</style>
