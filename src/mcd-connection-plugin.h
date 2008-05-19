/* -*- Mode: C; indent-tabs-mode: t; c-basic-offset: 4; tab-width: 8 -*- */
/*
 * This file is part of mission-control
 *
 * Copyright (C) 2008 Nokia Corporation. 
 *
 * Contact: Alberto Mardegan  <alberto.mardegan@nokia.com>
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public License
 * version 2.1 as published by the Free Software Foundation.
 *
 * This library is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA
 *
 */

#ifndef __MCD_CONNECTION_PLUGIN_H__
#define __MCD_CONNECTION_PLUGIN_H__

#include <glib.h>
#include <glib-object.h>
#include "mcd-plugin.h"

G_BEGIN_DECLS

typedef void (*McdAccountConnectionFunc) (McdAccount *account, GHashTable *parameters, gpointer userdata);

void mcd_account_connection_proceed (McdAccount *account, gboolean success);

#define MCD_ACCOUNT_CONNECTION_PRIORITY_POLICY 10000
#define MCD_ACCOUNT_CONNECTION_PRIORITY_TRANSPORT 20000
#define MCD_ACCOUNT_CONNECTION_PRIORITY_PARAMS   30000

void mcd_plugin_register_account_connection (McdPlugin *plugin,
					     McdAccountConnectionFunc func,
					     gint priority,
					     gpointer userdata);

G_END_DECLS

#endif /* __MCD_CONNECTION_PLUGIN_H__ */