const { initial } = require('../../utils/util')

Page({
  data: {
    bound: false,
    customer: null,
  },

  onShow() {
    const project = getApp().globalData.boundProject
    if (!project) {
      this.setData({ bound: false, customer: null })
      return
    }
    this.setData({
      bound: true,
      customer: {
        name: project.customer_name,
        phone: project.customer_phone,
        address: project.customer_address,
        contract: project.customer_contract,
        initial: initial(project.customer_name || '?'),
      },
    })
  },

  async bindOrder() {
    const ok = await getApp().bindOrder()
    if (ok) this.onShow()
  },

  /** 解绑订单：清空绑定状态，回到未绑定 */
  unbindOrder() {
    wx.showModal({
      title: '解绑订单',
      content: '确定要解绑当前订单吗？解绑后需要重新输入订单编号才能查看。',
      confirmColor: '#f43f5e',
      success: (res) => {
        if (!res.confirm) return
        getApp().clearBound()
        this.onShow()
      },
    })
  },
})
