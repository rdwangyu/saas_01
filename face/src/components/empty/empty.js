Component({
  properties: {
    text: {
      type: String,
      value: '暂无数据',
    },
    icon: {
      type: String,
      value: '📦',
    },
    showAction: {
      type: Boolean,
      value: false,
    },
    actionText: {
      type: String,
      value: '重新加载',
    },
  },

  methods: {
    onAction() {
      this.triggerEvent('action')
    },
  },
})
