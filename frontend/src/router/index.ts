import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('../views/HomeView.vue'),
    meta: {
      title: 'Narrative Assistant'
    }
  },
  {
    path: '/projects',
    name: 'projects',
    component: () => import('../views/ProjectsView.vue'),
    meta: {
      title: 'Proyectos - Narrative Assistant'
    }
  },
  {
    path: '/projects/:id',
    name: 'project',
    component: () => import('../views/ProjectDetailView.vue'),
    meta: {
      title: 'Proyecto - Narrative Assistant'
    }
  },
  {
    path: '/projects/:projectId/characters/:id',
    name: 'character',
    redirect: to => ({
      name: 'project',
      params: { id: to.params.projectId },
      query: { tab: 'entities', entity: to.params.id }
    })
  },
  {
    path: '/projects/:id/revision',
    name: 'revision',
    component: () => import('../views/RevisionView.vue'),
    meta: {
      title: 'Revision Intelligence - Narrative Assistant'
    }
  },
  {
    // Redirigir la ruta legacy de alertas al tab de alertas del proyecto
    path: '/projects/:id/alerts',
    name: 'alerts',
    redirect: to => ({
      name: 'project',
      params: { id: to.params.id },
      query: { tab: 'alerts' }
    })
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('../views/SettingsView.vue'),
    meta: {
      title: 'Configuración - Narrative Assistant'
    }
  },
  {
    path: '/collections',
    name: 'collections',
    component: () => import('../views/CollectionsView.vue'),
    meta: {
      title: 'Colecciones - Narrative Assistant'
    }
  },
  {
    path: '/collections/:id',
    name: 'collection-detail',
    component: () => import('../views/CollectionDetailView.vue'),
    meta: {
      title: 'Colección - Narrative Assistant'
    }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// Navigation guard para actualizar título
router.beforeEach((to, _from, next) => {
  document.title = (to.meta.title as string) || 'Narrative Assistant'
  next()
})

export default router
