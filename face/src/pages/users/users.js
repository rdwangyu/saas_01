const { request, clearTokens } = require('../../utils/request')
const { initial } = require('../../utils/util')

const PAGE_SIZE = 20

Page({
  data: {
    me: null,
    list: [],
    total: 0,
    page: 1,
    hasMore: true,
    loading: false,
    submitting: false,

    showAdd: false,
    showPwd: false,
    form: { username: '', email: '', password: '' },
    pwdForm: { password: '', confirm: '' },
  },

  onShow() {
    this.loadMe()
    this.loadList(true)
  },

  noop() {},

  onPullDownRefresh() {
    Promise.all([this.loadMe(), this.loadList(true)]).finally(() => wx.stopPullDownRefresh())
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadList(false)
    }
  },

  async loadMe() {
    try {
      const me = await request('/me/')
      this.setData({
        me: {
          ...me,
          initial: initial(me.username),
        },
      })
      getApp().globalData.userInfo = me
    } catch (err) {
      // 401 时 request 内部会跳转登录页
    }
  },

  async loadList(reset) {
    if (this.data.loading) return
    const page = reset ? 1 : this.data.page + 1
    this.setData({ loading: true })
    try {
      const data = await request(`/users/?page=${page}&page_size=${PAGE_SIZE}`)
      const items = (data.results || []).map((user) => ({
        ...user,
        initial: initial(user.username),
      }))
      this.setData({
        list: reset ? items : this.data.list.concat(items),
        total: data.count || 0,
        page,
        hasMore: !!data.next,
        loading: false,
      })
    } catch (err) {
      this.setData({ loading: false })
    }
  },

  /* ---------- 新增用户 ---------- */
  openAddModal() {
    this.setData({ showAdd: true, form: { username: '', email: '', password: '' } })
  },

  closeAddModal() {
    this.setData({ showAdd: false })
  },

  onFormInput(e) {
    const field = e.currentTarget.dataset.field
    this.setData({ [`form.${field}`]: e.detail.value })
  },

  async submitAdd() {
    const { username, email, password } = this.data.form
    if (!username.trim()) {
      wx.showToast({ title: '请输入用户名', icon: 'none' })
      return
    }
    if (!password) {
      wx.showToast({ title: '请输入初始密码', icon: 'none' })
      return
    }
    this.setData({ submitting: true })
    try {
      await request('/users/', {
        method: 'POST',
        data: { username: username.trim(), email: email.trim(), password },
      })
      wx.showToast({ title: '新增成功', icon: 'success' })
      this.setData({ showAdd: false })
      this.loadList(true)
    } catch (err) {
      wx.showToast({ title: err.message || '新增失败', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  },

  /* ---------- 删除用户 ---------- */
  onDelete(e) {
    const id = e.currentTarget.dataset.id
    const user = this.data.list.find((u) => u.id === id)
    if (!user) return
    wx.showModal({
      title: '删除用户',
      content: `确定删除用户「${user.username}」吗？删除后不可恢复。`,
      confirmColor: '#f43f5e',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await request(`/users/${id}/`, { method: 'DELETE' })
          wx.showToast({ title: '已删除', icon: 'success' })
          this.loadList(true)
        } catch (err) {
          wx.showToast({ title: err.message || '删除失败', icon: 'none' })
        }
      },
    })
  },

  /* ---------- 修改密码（当前用户） ---------- */
  openPwdModal() {
    this.setData({ showPwd: true, pwdForm: { password: '', confirm: '' } })
  },

  closePwdModal() {
    this.setData({ showPwd: false })
  },

  onPwdInput(e) {
    const field = e.currentTarget.dataset.field
    this.setData({ [`pwdForm.${field}`]: e.detail.value })
  },

  async submitPwd() {
    const { password, confirm } = this.data.pwdForm
    if (!password) {
      wx.showToast({ title: '请输入新密码', icon: 'none' })
      return
    }
    if (password.length < 6) {
      wx.showToast({ title: '密码至少 6 位', icon: 'none' })
      return
    }
    if (password !== confirm) {
      wx.showToast({ title: '两次输入的密码不一致', icon: 'none' })
      return
    }
    const me = this.data.me
    if (!me) return
    this.setData({ submitting: true })
    try {
      await request(`/users/${me.id}/`, {
        method: 'PATCH',
        data: { password },
      })
      wx.showToast({ title: '密码已修改', icon: 'success' })
      this.setData({ showPwd: false })
    } catch (err) {
      wx.showToast({ title: err.message || '修改失败', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  },

  /* ---------- 退出登录 ---------- */
  onLogout() {
    wx.showModal({
      title: '退出登录',
      content: '确定要退出当前账号吗？',
      success: (res) => {
        if (!res.confirm) return
        clearTokens()
        getApp().globalData.userInfo = null
        wx.reLaunch({ url: '/pages/login/login' })
      },
    })
  },
})
