const OSS_VIDEO = 'https://oss-pai-1qli472uu5uy3elgq8-cn-shanghai.oss-cn-shanghai.aliyuncs.com/ComfyUI_00001_.mp4?Expires=1783154236&OSSAccessKeyId=TMP.3KvZ237zmtxWLc2RvzomJkbQsKkfE2rG8XFaUKohTrLUGdWuZxarpRztMf7hBsT5c2PUnzsds64PB9BxL2LTgq4C1rguhn&Signature=sCifMvoY2uBI8K2tePM1DtOkRg0%3D'
App({
  onLaunch() {
    wx.getSystemInfo({ success: res => { this.globalData.systemInfo = res } })
  },
  globalData: {
    cases: [
      { id:1, title:'现代简约 · 云璟府 128㎡', meta:'三室两厅 · 128㎡ · 现代简约', desc:'黑白灰主调搭配原木色，开放式厨房+中岛台设计，全屋智能灯光系统。', img:'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=600&h=400&fit=crop', video: OSS_VIDEO },
      { id:2, title:'新中式 · 桃源里 168㎡', meta:'四室两厅 · 168㎡ · 新中式', desc:'水墨元素与现代家具融合，大面积落地窗，定制胡桃木护墙板+山水纹岩板电视墙。', img:'https://images.unsplash.com/photo-1618220179428-22790b461013?w=600&h=400&fit=crop', video: OSS_VIDEO },
      { id:3, title:'轻法式 · 翡翠湾 92㎡', meta:'两室两厅 · 92㎡ · 轻法式', desc:'奶油色+石膏线条+拱门造型，主卧L型衣帽间+梳妆台一体化，卫生间干湿三分离。', img:'https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?w=600&h=400&fit=crop', video: OSS_VIDEO },
      { id:4, title:'现代轻奢 · 白云府 145㎡', meta:'四室两厅 · 145㎡ · 现代轻奢', desc:'大理石+金属+玻璃材质搭配，7米横厅+落地窗，主卧套房配备独立衣帽间。', img:'https://images.unsplash.com/photo-1600573472550-8090b5e0745e?w=600&h=400&fit=crop', video: OSS_VIDEO },
      { id:5, title:'北欧风 · 清风苑 85㎡', meta:'两室一厅 · 85㎡ · 北欧风', desc:'白墙+浅色木地板+色彩点缀，客餐厅一体化，定制玄关鞋柜+餐边柜。', img:'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=600&h=400&fit=crop', video: OSS_VIDEO },
      { id:6, title:'日式原木 · 樱花府 98㎡', meta:'三室一厅 · 98㎡ · 日式原木', desc:'橡木、棉麻、藤编等自然材质，玄关下沉式落尘区，全屋收纳系统定制。', img:'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=600&h=400&fit=crop', video: OSS_VIDEO },
    ],
    project: {
      id:'BY20260601',
      name:'张先生',
      community:'云璟府',
      area:'128㎡',
      currentStage: 4,
      stages: ['拆除','水电','泥瓦','木工','油漆','安装'],
      stageDates: ['2026-04-01','2026-04-10','2026-04-22','2026-05-06','2026-05-18','2026-05-30'],
      photos: [
        'https://images.unsplash.com/photo-1590579491624-f98f36d4c307?w=300&h=200&fit=crop',
        'https://images.unsplash.com/photo-1581579438747-104c53d7fbc4?w=300&h=200&fit=crop',
        'https://images.unsplash.com/photo-1613665813446-82a78c468a1d?w=300&h=200&fit=crop',
        'https://images.unsplash.com/photo-1504307651254-5743aaf3d273?w=300&h=200&fit=crop',
        'https://images.unsplash.com/photo-1616486029423-aaa4789e8c9a?w=300&h=200&fit=crop',
        'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=300&h=200&fit=crop',
        'https://images.unsplash.com/photo-1600566753376-12c8ab7e2edb?w=300&h=200&fit=crop',
        'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=300&h=200&fit=crop',
        'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=300&h=200&fit=crop',
        'https://images.unsplash.com/photo-1600573472550-8090b5e0745e?w=300&h=200&fit=crop',
        'https://images.unsplash.com/photo-1618220179428-22790b461013?w=300&h=200&fit=crop',
        'https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?w=300&h=200&fit=crop',
        'https://images.unsplash.com/photo-1600585152915-d208bec867a1?w=300&h=200&fit=crop',
        'https://images.unsplash.com/photo-1600585153490-76fb20a32601?w=300&h=200&fit=crop',
        'https://images.unsplash.com/photo-1616594453589-e9ebc7375ad0?w=300&h=200&fit=crop',
        'https://images.unsplash.com/photo-1595526114035-0d45ed16cfbf?w=300&h=200&fit=crop',
        'https://images.unsplash.com/photo-1600585154084-4e5fe7c39198?w=300&h=200&fit=crop',
        'https://images.unsplash.com/photo-1600573472591-ee6b68d14c68?w=300&h=200&fit=crop',
      ]
    }
  }
})
